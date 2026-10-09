"""ThreadManager 的业务逻辑层：处理帖子删除、互斥标签、反应补录与发布更新。"""

import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List
import discord

from core.config_repository import ConfigRepository
from core.thread_repository import ThreadRepository
from core.thread_deletion_service import ThreadDeletionService
from shared.enum import SearchConfigType
from shared.redis_client import RedisManager
from shared.similar_threads_cache import invalidate_similar_candidate_pools

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class ThreadLogic:
    """ThreadManager 的核心业务逻辑处理器"""

    def __init__(self, bot: "MyBot", session_factory, config: dict, sync_service):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.sync_service = sync_service

    # ---------------------------------------------------------
    # 删除处理逻辑
    # ---------------------------------------------------------
    async def delete_thread_permanently(self, thread_id: int):
        """处理整个帖子被从 Discord 删除的逻辑：物理删除数据库记录"""
        async with self.session_factory() as session:
            await ThreadDeletionService(session).delete_thread(thread_id)
            await session.commit()
            logger.info(f"帖子 {thread_id} 已从 Discord 删除，已同步清理数据库索引记录")
        await self._invalidate_similarity_cache(thread_id)

    async def handle_first_message_deletion(self, thread: discord.Thread):
        """处理首楼被删除但帖子还在的逻辑：隐藏并发送恢复按钮"""
        async with self.session_factory() as session:
            repo = ThreadRepository(session)
            # 逻辑隐藏 (show_flag=False)
            success = await repo.update_thread_visibility(thread.id, show_flag=False)

        if not success:
            return

        await self._invalidate_similarity_cache(thread.id)

        logger.info(f"帖子 {thread.id}(频道:{thread.parent_id}) 首楼被删，已将其隐藏")

        # if not thread.owner_id:
        #     return

        # # 发送恢复按钮视图
        # view = ThreadVisibilityView(self.bot, self.session_factory)
        # content = (
        #     f"<@{thread.owner_id}>\n"
        #     f"系统检测到您的首楼消息已被删除，为防止死链，**本帖已自动从新搜索系统中隐藏**。\n"
        #     f"如果您仍希望本帖在搜索中可见（例如您已在楼中补档），请点击下方按钮重新开放可见性。"
        # )

        # try:
        #     await self.bot.api_scheduler.submit(
        #         coro_factory=lambda: thread.send(content=content, view=view),
        #         priority=3
        #     )
        # except Exception as e:
        #     logger.error(f"向帖子 {thread.id} 发送可见性视图失败", exc_info=True)

    async def _invalidate_similarity_cache(self, thread_id: int) -> None:
        """尽力失效源帖的相似推荐候选池。"""
        try:
            await invalidate_similar_candidate_pools(
                RedisManager.get_client(), thread_id
            )
        except Exception:
            logger.warning(
                "失效相似帖子候选池失败: thread_id=%s", thread_id, exc_info=True
            )

    # ---------------------------------------------------------
    # 互斥标签逻辑
    # ---------------------------------------------------------
    async def apply_mutex_tag_rules(self, thread: discord.Thread) -> bool:
        """检查并应用互斥标签规则。如果进行了修改，则返回 True。"""
        applied_tags = thread.applied_tags
        if (
            not applied_tags
            or len(applied_tags) < 2
            or not thread.parent
            or not isinstance(thread.parent, discord.ForumChannel)
        ):
            return False

        post_tag_name_to_obj = {tag.name: tag for tag in applied_tags}
        post_tag_names = set(post_tag_name_to_obj.keys())

        async with self.session_factory() as session:
            repo = ConfigRepository(session)
            groups = await repo.get_all_mutex_groups_with_rules()
            notify_config = await repo.get_search_config(
                SearchConfigType.NOTIFY_ON_MUTEX_CONFLICT
            )
            should_notify_management = notify_config and notify_config.value_int == 1

            tags_to_remove, tags_to_add = set(), set()
            all_conflicts = []

            for group in groups:
                sorted_rules = sorted(group.rules, key=lambda r: r.priority)
                group_tag_names = {rule.tag_name for rule in sorted_rules}
                conflicting_names = post_tag_names.intersection(group_tag_names)

                if len(conflicting_names) > 1:
                    override_tag_obj = None
                    if group.override_tag_name:
                        override_tag_obj = discord.utils.get(
                            thread.parent.available_tags, name=group.override_tag_name
                        )

                    if override_tag_obj:
                        for name in conflicting_names:
                            tags_to_remove.add(post_tag_name_to_obj[name])
                        tags_to_add.add(override_tag_obj)
                        all_conflicts.append(
                            {
                                "group": group,
                                "removed": conflicting_names,
                                "added": override_tag_obj.name,
                            }
                        )
                    else:
                        highest_priority_tag_name = next(
                            (
                                rule.tag_name
                                for rule in sorted_rules
                                if rule.tag_name in conflicting_names
                            ),
                            "",
                        )
                        tags_to_remove_from_group = {
                            post_tag_name_to_obj[name]
                            for name in conflicting_names
                            if name != highest_priority_tag_name
                        }
                        tags_to_remove.update(tags_to_remove_from_group)
                        all_conflicts.append(
                            {
                                "group": group,
                                "removed": {t.name for t in tags_to_remove_from_group},
                                "added": None,
                            }
                        )

            if tags_to_remove or tags_to_add:
                if all_conflicts:
                    user_notified_publicly = await self._notify_user_of_mutex_removal(
                        thread, all_conflicts
                    )
                    if should_notify_management:
                        await self._notify_management_of_mutex_conflict(
                            thread, all_conflicts, user_notified_publicly
                        )

                final_tags = list((set(applied_tags) - tags_to_remove) | tags_to_add)
                try:
                    await self.bot.api_scheduler.submit(
                        coro_factory=lambda: thread.edit(applied_tags=final_tags),
                        priority=2,
                    )
                    return True
                except Exception:
                    logger.error(
                        f"自动修改帖子 {thread.id} 的标签时失败", exc_info=True
                    )
                    return False
        return False

    async def _notify_user_of_mutex_removal(
        self, thread: discord.Thread, conflicts: List[Dict[str, Any]]
    ) -> bool:
        """通知用户他们的帖子因为互斥规则被修改了。如果发送了公开通知，则返回 True。"""
        if not thread.owner:
            logger.warning(f"无法获取帖子 {thread.id} 的作者，无法发送通知。")
            return False

        author = thread.owner

        parent_channel_str = "未知频道"
        if thread.parent:
            parent_channel_str = f"[{thread.parent.name}]({thread.parent.jump_url})"

        embed = discord.Embed(
            title="🏷️ 帖子标签自动修改通知",
            description=f"您发表在 {thread.guild.name} > {parent_channel_str} 的帖子 "
            f"[{thread.name}]({thread.jump_url})\n"
            f"其标签已被自动修改",
            color=discord.Color.orange(),
        )
        embed.add_field(name="原因", value="触发了互斥标签规则", inline=False)

        for i, conflict_info in enumerate(conflicts):
            group = conflict_info["group"]
            removed_tags = conflict_info["removed"]
            added_tag = conflict_info["added"]

            sorted_rules = sorted(group.rules, key=lambda r: r.priority)

            group_tags_list = []
            if group.override_tag_name:
                group_tags_list.append(f"覆盖标签: **{group.override_tag_name}**")

            priority_rules_list = [
                f"优先级 {j + 1}: **{rule.tag_name}**"
                for j, rule in enumerate(sorted_rules)
            ]
            group_tags_list.extend(priority_rules_list)

            group_tags_str = "\n".join(group_tags_list)

            removed_tags_str = ", ".join(f"{t}" for t in removed_tags)
            value_parts = [f"**规则**:\n{group_tags_str}"]

            if added_tag:
                value_parts.append(f"**结果**: \n应用覆盖标签: **{added_tag}**")
                value_parts.append(f"移除标签: **{removed_tags_str}**")
            else:
                value_parts.append("**结果**: \n保留最高优先级标签")
                value_parts.append(f"移除标签: **{removed_tags_str}**")

            embed.add_field(
                name=f"冲突组 {i + 1}",
                value="\n".join(value_parts),
                inline=False,
            )

        footer_text = (
            "如需修改，请右键点击左侧频道列表中的帖子名，\n选择'编辑帖子'来调整标签"
        )
        embed.set_footer(text=footer_text)

        try:
            # 尝试通过调度器发送私信
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: author.send(embed=embed), priority=5
            )
            logger.debug(f"已向用户 {author.id} 发送互斥标签移除私信通知")
            return False
        except discord.Forbidden:
            logger.warning(f"无法向用户 {author.id} 发送私信，将在原帖中发送公开通知")
            # 发送备用公开通知
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: thread.send(
                    content=f":crying_cat_face: \n{author.mention}，您的帖子标签将被修改，详情请见下方解释",
                    embed=embed,
                ),
                priority=5,
            )
            return True
        except Exception as e:
            logger.error(f"向用户 {author.id} 发送私信时发生未知错误。", exc_info=e)
            return False

    async def _notify_management_of_mutex_conflict(
        self,
        thread: discord.Thread,
        conflicts: List[Dict[str, Any]],
        user_notified_publicly: bool,
    ):
        """在帖子中通知管理组发生了互斥标签冲突。"""
        management_role_id = self.bot.config.get("management_role_id")
        if not management_role_id:
            logger.warning(
                "未在 config.json 中配置 management_role_id，无法发送管理通知。"
            )
            return

        content = f"<@&{management_role_id}>"
        embed = None

        # 仅当没有在帖子内公开通知用户时，才创建 embed
        if not user_notified_publicly:
            embed = discord.Embed(
                title="检测到互斥标签",
                description=f"帖子 [{thread.name}]({thread.jump_url}) 存在互斥标签",
                color=discord.Color.greyple(),
            )

            for i, conflict_info in enumerate(conflicts):
                group = conflict_info["group"]
                removed_tags = conflict_info["removed"]
                added_tag = conflict_info["added"]

                sorted_rules = sorted(group.rules, key=lambda r: r.priority)

                group_tags_list = []
                if group.override_tag_name:
                    group_tags_list.append(f"覆盖标签: **{group.override_tag_name}**")

                priority_rules_list = [
                    f"优先级 {j + 1} : **{rule.tag_name}**"
                    for j, rule in enumerate(sorted_rules)
                ]
                group_tags_list.extend(priority_rules_list)

                group_tags_str = "\n".join(group_tags_list)

                removed_tags_str = ", ".join(f"{t}" for t in removed_tags)
                value_parts = [f"**规则**:\n{group_tags_str}"]

                if added_tag:
                    value_parts.append(f"**结果**: \n应用覆盖标签: **{added_tag}**")
                    value_parts.append(f"移除标签: **{removed_tags_str}**")
                else:
                    value_parts.append("**结果**: \n保留最高优先级标签")
                    value_parts.append(f"移除标签: **{removed_tags_str}**")

                embed.add_field(
                    name=f"冲突组 {i + 1}",
                    value="\n".join(value_parts),
                    inline=False,
                )

        async def send_notification():
            if embed:
                await thread.send(content=content, embed=embed)
            else:
                await thread.send(content=content)

        await self.bot.api_scheduler.submit(
            coro_factory=send_notification,
            priority=3,
        )
        logger.debug(f"已在帖子 {thread.id} 中发送互斥标签管理通知。")

    # ---------------------------------------------------------
    # 其他零散逻辑 (预同步、反应补录、指令逻辑)
    # ---------------------------------------------------------
    async def pre_sync_forum_tags(self, channel: discord.ForumChannel):
        """预同步一个论坛频道的所有可用标签"""
        await self.sync_service.pre_sync_forum_tags(channel)

    async def process_publish_update(
        self,
        interaction: discord.Interaction,
        thread: discord.Thread,
        message_link: str,
    ):
        """处理发布更新的指令逻辑"""
        link_pattern = r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)"
        if not re.match(link_pattern, message_link):
            await interaction.followup.send("❌ 消息链接格式不正确", ephemeral=True)
            return

        async with self.session_factory() as session:
            repo = ThreadRepository(session)
            success = await repo.update_thread_update_info(thread.id, message_link)

            if success:
                embed = discord.Embed(
                    title="📢 帖子有新更新！",
                    description=f"作者发布了新内容：\n{message_link}",
                    color=discord.Color.green(),
                )
                if isinstance(
                    interaction.channel, (discord.TextChannel, discord.Thread)
                ):
                    await interaction.channel.send(embed=embed)
                await interaction.followup.send("✅ 更新发布成功！", ephemeral=True)
            else:
                await interaction.followup.send(
                    "❌ 发布失败，可能是帖子尚未被系统索引", ephemeral=True
                )
