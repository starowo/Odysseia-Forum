import logging
import discord
from typing import List, TYPE_CHECKING

from shared.safe_defer import safe_defer
from config.repository import ConfigRepository
from config.views.mutex_config_view import MutexConfigView
from config.views.components.delete_group_modal import DeleteGroupModal
from config.views.add_mutex_group_view import AddMutexGroupView
from shared.api_scheduler import APIScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker

if TYPE_CHECKING:
    from bot_main import MyBot
    from core.tagService import TagService

logger = logging.getLogger(__name__)

class MutexTagsHandler:
    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        api_scheduler: APIScheduler,
        tag_service: "TagService",
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.api_scheduler = api_scheduler
        self.tag_service = tag_service

    async def start_configuration_flow(self, interaction: discord.Interaction):
        """开始配置流程，发送初始面板。"""
        await safe_defer(interaction,ephemeral=True)
        
        view: MutexConfigView = MutexConfigView(self, self.tag_service.get_unique_tag_names(),interaction)
        embed = await self.build_embed()
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def build_embed(self) -> discord.Embed:
        """构建显示当前规则的Embed。"""
        embed = discord.Embed(
            title="⚔️ 互斥标签组配置",
            description="在这里管理帖子中不能共存的标签组。\n组内标签按优先级从高到低排列。",
            color=0xE74C3C
        )
        async with self.session_factory() as session:
            repo = ConfigRepository(session)
            groups = await repo.get_all_mutex_groups_with_rules()

        if not groups:
            embed.add_field(name="当前没有互斥组", value="点击“新增”来创建第一个吧！")
        else:
            for group in groups:
                sorted_rules = sorted(group.rules, key=lambda r: r.priority)
                value_str = " ➡️ ".join(f"`{rule.tag_name}`" for rule in sorted_rules)
                embed.add_field(name=f"互斥组 ID: {group.id}", value=value_str, inline=False)
        return embed

    async def handle_save_new_group(self, interaction: discord.Interaction, view: AddMutexGroupView):
        """处理保存新互斥组的逻辑"""
        await safe_defer(interaction)
        
        processed_tags = [tag for tag in view.selected_tags if tag]
        
        unique_tags = list(dict.fromkeys(processed_tags))
        if len(unique_tags) < 2:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send("❌ 至少需要选择两个不同的标签来组成一个互斥组。", ephemeral=True),
                priority=1,
            )
            return
        
        async with self.session_factory() as session:
            repo = ConfigRepository(session)
            await repo.add_mutex_group(unique_tags)
        
        # 在保存成功后，关闭 AddMutexGroupView 消息
        await self.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.delete_original_response(),
            priority=1,
        )
        
        # 刷新原始消息
        await self.refresh_view(view.father_interaction)
        
    async def handle_delete_group(self, interaction: discord.Interaction, view: MutexConfigView):
        """处理删除按钮点击，弹出模态框。"""
        modal = DeleteGroupModal(self, view)
        await interaction.response.send_modal(modal)

    async def process_delete_modal(self, interaction: discord.Interaction, group_id_str: str, view: MutexConfigView):
        """处理删除模态框的提交。"""
        await interaction.response.defer(ephemeral=True)
        try:
            group_id = int(group_id_str)
            async with self.session_factory() as session:
                repo = ConfigRepository(session)
                success = await repo.delete_mutex_group(group_id)
            
            if success:
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(f"✅ 已成功删除互斥组 ID: {group_id}。", ephemeral=True),
                    priority=1,
                )
            else:
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(f"⚠️ 未找到 ID 为 {group_id} 的互斥组。", ephemeral=True),
                    priority=1,
                )

            # 刷新原始消息
            await self.refresh_view(interaction)

        except ValueError:
            await interaction.followup.send("❌ ID必须是一个有效的数字。", ephemeral=True)
        except Exception as e:
            logger.error("删除互斥组时出错", exc_info=e)
            await interaction.followup.send(f"❌ 删除失败: {e}", ephemeral=True)

    async def refresh_view(self, interaction: discord.Interaction):
        """刷新 MutexConfigView 视图的embed"""
        embed = await self.build_embed()
        await self.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.edit_original_response(embed=embed),
            priority=1,
        )