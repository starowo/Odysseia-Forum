import discord
from discord import app_commands
from discord.ext import commands
import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker
from typing import TYPE_CHECKING, List, Tuple, Any

from shared.safe_defer import safe_defer
from src.config.repository import ConfigRepository

if TYPE_CHECKING:
    from bot_main import MyBot
    from src.core.sync_service import SyncService
from .repository import ThreadManagerRepository
from .views.vote_view import TagVoteView

import logging

logger = logging.getLogger(__name__)


from src.core.cache_service import CacheService


class ThreadManager(commands.Cog):
    """处理标签同步与评价"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
        cache_service: CacheService,
        sync_service: "SyncService",
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.cache_service = cache_service
        self.sync_service = sync_service
        logger.info("ThreadManager 模块已加载")

    def is_channel_indexed(self, channel_id: int) -> bool:
        """检查频道是否已索引"""
        return self.cache_service.is_channel_indexed(channel_id)

    async def _notify_user_of_mutex_removal(self, thread: discord.Thread, conflicts: List[Tuple[Any, set]]):
        """通知用户他们的帖子因为互斥规则被修改了。"""
        if not thread.owner:
            logger.warning(f"无法获取帖子 {thread.id} 的作者，无法发送通知。")
            return

        author = thread.owner

        parent_channel_str = '未知频道'
        if thread.parent:
            parent_channel_str = f"[{thread.parent.name}]({thread.parent.jump_url})"
        
        embed = discord.Embed(
            title="🏷️ 帖子标签自动修改通知",
            description=f"您发表在 {thread.guild.name} > {parent_channel_str} 的帖子 "
                        f"[{thread.name}]({thread.jump_url})\n"
                        f"其标签已被自动修改",
            color=discord.Color.orange()
        )
        embed.add_field(name="原因", value="触发了互斥标签规则", inline=False)

        for i, (group, removed_tags_for_group) in enumerate(conflicts):
            sorted_rules = sorted(group.rules, key=lambda r: r.priority)
            group_tags_list = [f"优先级 {j+1} : {rule.tag_name}" for j, rule in enumerate(sorted_rules)]
            group_tags_str = "\n".join(group_tags_list)
            
            embed.add_field(
                name=f"冲突组 {i+1}",
                value=f"**规则**:\n{group_tags_str}\n**被移除的标签**:\n{', '.join(removed_tags_for_group)}",
                inline=False
            )
        
        embed.set_footer(text="系统自动保留了冲突组中优先级最高的标签\n请右键点击左侧频道列表中的帖子名，对标签进行修改\n选择其中一个标签进行保留")

        async def send_dm():
            try:
                await author.send(embed=embed)
                logger.info(f"已向用户 {author.id} 发送互斥标签移除私信通知。")
            except discord.Forbidden:
                logger.warning(f"无法向用户 {author.id} 发送私信，将在原帖中发送公开通知。")
                # 发送备用公开通知
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: thread.send(content=f"{author.mention}，你的帖子标签已被修改，详情请见上方通知。", embed=embed),
                    priority=3
                )
            except Exception as e:
                logger.error(f"向用户 {author.id} 发送私信时发生未知错误。", exc_info=e)
        
        await self.bot.api_scheduler.submit(coro_factory=send_dm, priority=3)

    async def apply_mutex_tag_rules(self, thread: discord.Thread) -> bool:
        """检查并应用互斥标签规则。如果进行了修改，则返回 True。"""
        applied_tags = thread.applied_tags
        if not applied_tags or len(applied_tags) < 2:
            return False

        post_tag_name_to_id = {tag.name: tag.id for tag in applied_tags}
        post_tag_names = set(post_tag_name_to_id.keys())

        async with self.session_factory() as session:
            repo = ConfigRepository(session) # 使用新的ConfigRepository
            groups = await repo.get_all_mutex_groups_with_rules()

        tags_to_remove_ids = set()
        all_conflicts = [] # 收集所有冲突信息

        for group in groups:
            sorted_rules = sorted(group.rules, key=lambda r: r.priority)
            conflicting_names = [rule.tag_name for rule in sorted_rules if rule.tag_name in post_tag_names]

            # 如果帖子的标签中，有超过一个（含）的标签在本互斥组内
            if len(conflicting_names) > 1:
                group_tags_to_remove = set(conflicting_names[1:])
                # 保留优先级最高的（第一个），移除其他的
                for name_to_remove in group_tags_to_remove:
                    tags_to_remove_ids.add(post_tag_name_to_id[name_to_remove])
                
                # 记录冲突信息
                all_conflicts.append((group, group_tags_to_remove))

        if tags_to_remove_ids:
            # 发送通知 (一次性发送所有冲突)
            if all_conflicts:
                await self._notify_user_of_mutex_removal(thread, all_conflicts)

            # 使用列表推导式创建新的标签列表
            final_tags = [tag for tag in applied_tags if tag.id not in tags_to_remove_ids]
            
            # 使用集合推导式获取被移除的标签名称
            removed_tag_names = {tag.name for tag in applied_tags if tag.id in tags_to_remove_ids}
            logger.info(f"帖子 {thread.id} 发现互斥标签，将移除: {', '.join(removed_tag_names)}")

            try:
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: thread.edit(applied_tags=final_tags),
                    priority=2
                )
                return True
            except Exception as e:
                logger.error(f"自动修改帖子 {thread.id} 的标签时失败", exc_info=e)
        
        return False

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if self.is_channel_indexed(channel_id=thread.parent_id):
            modified = await self.apply_mutex_tag_rules(thread)
            if modified:
                # 标签被修改，on_thread_update会被触发，届时再同步
                return
            await self.sync_service.sync_thread(thread=thread)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if (
            self.is_channel_indexed(channel_id=after.parent_id)
            and (before.applied_tags != after.applied_tags or before.name != after.name)
        ):
            modified = await self.apply_mutex_tag_rules(after)
            if modified:
                # 标签被修改，会再次触发 on_thread_update，届时再同步
                return
            await self.sync_service.sync_thread(thread=after)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        if self.is_channel_indexed(thread.parent_id):
            async with self.session_factory() as session:
                repo = ThreadManagerRepository(session=session)
                await repo.delete_thread_index(thread_id=thread.id)
            # 缓存现在由全局事件处理，此处不再需要手动刷新

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            not message.guild
            or not isinstance(message.channel, discord.Thread)
            or message.author.bot
        ):
            return

        thread = message.channel
        # 如果是首楼消息，则忽略，因为 sync_thread 会处理
        if thread.id == message.id:
            return

        if self.is_channel_indexed(thread.parent_id):
            async with self.session_factory() as session:
                repo = ThreadManagerRepository(session)
                await repo.increment_reply_count(thread.id, message.created_at)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if not payload.guild_id:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread) and self.is_channel_indexed(
                channel.parent_id
            ):
                # 如果是首楼消息被编辑，需要重新同步整个帖子
                if payload.message_id == channel.id:
                    # 因为这是 raw 事件，缓存的 channel 对象可能不是最新的
                    # 我们需要确保同步的是最完整的数据
                    await self.sync_service.sync_thread(
                        thread=channel, fetch_if_incomplete=True
                    )
                else:
                    # 普通消息编辑只更新活跃时间
                    async with self.session_factory() as session:
                        repo = ThreadManagerRepository(session)
                        # payload 中没有编辑时间，所以我们用当前时间
                        await repo.update_thread_last_active_at(
                            channel.id, datetime.datetime.now(datetime.timezone.utc)
                        )
        except Exception:
            logger.warning("处理消息编辑事件失败", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if not payload.guild_id:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread) and self.is_channel_indexed(
                channel.parent_id
            ):
                # 如果首楼被删除，删除整个索引
                if payload.message_id == channel.id:
                    async with self.session_factory() as session:
                        repo = ThreadManagerRepository(session=session)
                        await repo.delete_thread_index(thread_id=channel.id)
                    # 缓存现在由全局事件处理，此处不再需要手动刷新
                else:
                    # 普通消息删除，只更新回复数
                    async with self.session_factory() as session:
                        repo = ThreadManagerRepository(session)
                        await repo.decrement_reply_count(channel.id)
        except Exception:
            logger.warning("处理消息删除事件失败", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread) and self.is_channel_indexed(
                channel.parent_id
            ):
                # 只有对首楼消息的反应才更新统计
                if payload.message_id == channel.id:
                    await self.bot.api_scheduler.submit(
                        coro_factory=lambda: self._update_reaction_count(channel),
                        priority=5,
                    )
        except Exception:
            logger.warning("处理反应添加事件失败", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread) and self.is_channel_indexed(
                channel.parent_id
            ):
                # 只有对首楼消息的反应才更新统计
                if payload.message_id == channel.id:
                    await self.bot.api_scheduler.submit(
                        coro_factory=lambda: self._update_reaction_count(channel),
                        priority=5,
                    )
        except Exception:
            logger.warning("处理反应移除事件失败", exc_info=True)

    async def _update_reaction_count(self, thread: discord.Thread):
        """(协程) 更新帖子的反应数"""
        try:
            # 优先从缓存获取，失败则API调用
            first_msg = thread.get_partial_message(thread.id)
            first_msg = await first_msg.fetch()

            reaction_count = (
                max([r.count for r in first_msg.reactions])
                if first_msg.reactions
                else 0
            )

            async with self.session_factory() as session:
                repo = ThreadManagerRepository(session)
                await repo.update_thread_reaction_count(thread.id, reaction_count)
        except Exception:
            logger.warning(f"更新反应数失败 (帖子ID: {thread.id})", exc_info=True)

    async def pre_sync_forum_tags(self, channel: discord.ForumChannel):
        """
        预同步一个论坛频道的所有可用标签，确保它们都存在于数据库中。
        """
        logger.debug(
            f"开始为频道 '{channel.name}' (ID: {channel.id}) 预同步所有可用标签..."
        )
        if not channel.available_tags:
            logger.debug(
                f"频道 '{channel.name}' (ID: {channel.id}) 没有任何可用标签，跳过同步。"
            )
            return

        tags_data = {tag.id: tag.name for tag in channel.available_tags}

        try:
            async with self.session_factory() as session:
                repo = ThreadManagerRepository(session=session)
                await repo.get_or_create_tags(tags_data)
            logger.debug(
                f"为频道 '{channel.name}' (ID: {channel.id}) 预同步了 {len(tags_data)} 个标签。"
            )
        except Exception as e:
            logger.error(
                f"为频道 '{channel.name}' (ID: {channel.id}) 预同步标签时出错: {e}",
                exc_info=True,
            )
            # 即使这里失败，我们也不应该中断整个索引过程，
            # 因为后续的 consumer 仍然有机会（虽然有风险）去创建标签。
            # 抛出异常让调用者决定如何处理。
            raise

    @app_commands.command(
        name="标签评价", description="对当前帖子的标签进行评价（赞或踩）"
    )
    async def tag_rate(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        "此命令只能在帖子中使用。", ephemeral=True
                    ),
                    priority=1,
                )
                return

            if not interaction.channel.applied_tags:
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        "该帖子没有应用任何标签。", ephemeral=True
                    ),
                    priority=1,
                )
                return

            tag_map = {tag.id: tag.name for tag in interaction.channel.applied_tags}

            view = TagVoteView(
                thread_id=interaction.channel.id,
                thread_name=interaction.channel.name,
                tag_map=tag_map,
                session_factory=self.session_factory,
                api_scheduler=self.bot.api_scheduler,
            )
            # 获取初始统计数据
            async with self.session_factory() as session:
                repo = ThreadManagerRepository(session)
                initial_stats = await repo.get_tag_vote_stats(
                    interaction.channel.id, tag_map
                )

            # 使用初始统计数据创建嵌入
            embed = view.create_embed(initial_stats)

            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    embed=embed, view=view, ephemeral=True
                ),
                priority=1,
            )
        except Exception as e:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    f"❌ 命令执行失败: {e}", ephemeral=True
                ),
                priority=1,
            )
