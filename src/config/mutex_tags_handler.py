import logging
from typing import TYPE_CHECKING, List, Optional

import discord
from sqlalchemy.ext.asyncio import async_sessionmaker

from config.config_service import ConfigService
from config.views.add_mutex_group_view import AddMutexGroupView
from config.views.components.delete_group_modal import DeleteGroupModal
from config.views.mutex_config_view import MutexConfigView
from shared.api_scheduler import APIScheduler
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from bot_main import MyBot
    from core.tag_cache_service import TagCacheService

logger = logging.getLogger(__name__)


class MutexTagsHandler:
    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        api_scheduler: APIScheduler,
        tag_service: "TagCacheService",
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.api_scheduler = api_scheduler
        self.tag_service = tag_service

    async def start_configuration_flow(self, interaction: discord.Interaction):
        """开始配置流程，发送初始面板。"""
        await safe_defer(interaction, ephemeral=True)

        view: MutexConfigView = MutexConfigView(
            self, self.tag_service.get_unique_tag_names(), interaction
        )
        embed = await self.build_embed()

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def build_embed(
        self, selected_priority_tags: Optional[List[str]] = None
    ) -> discord.Embed:
        """构建显示当前规则的Embed。"""
        embed = discord.Embed(
            title="⚔️ 互斥标签组配置",
            description="在这里管理帖子中不能共存的标签组。\n组内标签按优先级从高到低排列。",
            color=0xE74C3C,
        )
        async with self.session_factory() as session:
            repo = ConfigService(session)
            groups = await repo.get_all_mutex_groups_with_rules()

        if not groups and not selected_priority_tags:
            embed.add_field(name="当前没有互斥组", value="点击'新增'来创建第一个吧！")
        else:
            for group in groups:
                group_name = f"互斥组 ID: {group.id}"
                if group.override_tag_name:
                    group_name += f" (覆盖标签: `{group.override_tag_name}`)"

                sorted_rules = sorted(group.rules, key=lambda r: r.priority)
                value_str = " ➡️ ".join(f"`{rule.tag_name}`" for rule in sorted_rules)
                embed.add_field(name=group_name, value=value_str, inline=False)
        return embed

    def _create_step1_view(
        self,
        father_interaction: discord.Interaction,
        selected_tags: Optional[List[str]] = None,
    ) -> AddMutexGroupView:
        """创建一个用于步骤1的视图实例。"""
        return AddMutexGroupView(
            handler=self,
            all_tag_names=self.tag_service.get_unique_tag_names(),
            father_interaction=father_interaction,
            step=1,
            selected_priority_tags=selected_tags,
        )

    async def handle_add_group_start(
        self, interaction: discord.Interaction, father_interaction: discord.Interaction
    ):
        """处理从主面板点击“新增”的流程，发送一个新的临时消息。"""
        await safe_defer(interaction, ephemeral=True)
        view = self._create_step1_view(father_interaction)
        await interaction.followup.send(
            embed=view.build_embed(), view=view, ephemeral=True
        )

    async def handle_back_to_step1(
        self, interaction: discord.Interaction, view: AddMutexGroupView
    ):
        """处理从步骤2点击“上一步”的流程，编辑现有消息返回步骤1。"""
        await safe_defer(interaction, ephemeral=True)

        new_view = self._create_step1_view(view.father_interaction, view.selected_tags)
        await interaction.edit_original_response(
            embed=new_view.build_embed(), view=new_view
        )

    async def handle_add_group_step2(
        self, interaction: discord.Interaction, view: AddMutexGroupView
    ):
        """处理“下一步”按钮点击，显示步骤2的视图。"""
        await safe_defer(interaction, ephemeral=True)

        # 校验步骤1的数据
        processed_tags = [tag for tag in view.selected_tags if tag]
        unique_tags = list(dict.fromkeys(processed_tags))
        if len(unique_tags) < 2:
            await interaction.followup.send(
                "❌ 至少需要选择两个不同的标签来组成一个互斥组", ephemeral=True
            )
            return

        # 更新视图到步骤2
        new_view = AddMutexGroupView(
            handler=self,
            all_tag_names=self.tag_service.get_unique_tag_names(),
            father_interaction=view.father_interaction,  # 传递父交互
            step=2,
            selected_priority_tags=unique_tags,
        )

        await interaction.edit_original_response(
            embed=new_view.build_embed(), view=new_view
        )

    async def handle_save_new_group(
        self, interaction: discord.Interaction, view: AddMutexGroupView
    ):
        """处理最终的保存逻辑。"""
        await safe_defer(interaction, ephemeral=True)

        priority_tags = [tag for tag in view.selected_tags if tag]
        override_tag_name = (
            view.selected_override_tag if view.selected_override_tag else None
        )

        async with self.session_factory() as session:
            repo = ConfigService(session)
            await repo.add_mutex_group(priority_tags, override_tag_name)
            logger.info(
                f"成功添加新的互斥标签组，包含标签: {priority_tags}，覆盖标签: {override_tag_name}"
            )

        # 在保存成功后，关闭 AddMutexGroupView 消息
        await interaction.delete_original_response()

        # 刷新主配置面板
        await self.refresh_view(view.father_interaction)

    async def handle_delete_group(
        self, interaction: discord.Interaction, view: MutexConfigView
    ):
        """处理删除按钮点击，弹出模态框。"""
        modal = DeleteGroupModal(self, view)
        await interaction.response.send_modal(modal)

    async def process_delete_modal(
        self, interaction: discord.Interaction, group_id_str: str, view: MutexConfigView
    ):
        """处理删除模态框的提交。"""
        await interaction.response.defer(ephemeral=True)
        try:
            group_id = int(group_id_str)
            async with self.session_factory() as session:
                repo = ConfigService(session)
                success = await repo.delete_mutex_group(group_id)

            if success:
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        f"✅ 已成功删除互斥组 ID: {group_id}。", ephemeral=True
                    ),
                    priority=1,
                )
            else:
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        f"⚠️ 未找到 ID 为 {group_id} 的互斥组。", ephemeral=True
                    ),
                    priority=1,
                )

            # 刷新原始消息
            await self.refresh_view(interaction)

        except ValueError:
            await interaction.followup.send(
                "❌ ID必须是一个有效的数字。", ephemeral=True
            )
        except Exception as e:
            logger.error("删除互斥组时出错", exc_info=e)
            await interaction.followup.send(f"❌ 删除失败: {e}", ephemeral=True)

    async def refresh_view(self, interaction: discord.Interaction):
        """刷新 MutexConfigView 视图的embed"""
        embed = await self.build_embed()
        original_message = await interaction.original_response()
        await self.bot.api_scheduler.submit(
            coro_factory=lambda: original_message.edit(embed=embed),
            priority=1,
        )
