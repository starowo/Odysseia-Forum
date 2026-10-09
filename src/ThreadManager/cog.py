"""ThreadManager Cog：监听 Discord 事件并调度帖子同步、状态更新与标签评价。"""

import asyncio
import datetime
from typing import TYPE_CHECKING
import discord
from discord.ext import commands
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.follow_repository import ThreadFollowRepository
from core.thread_repository import ThreadRepository
from shared.safe_defer import safe_defer
from shared.enum import ConstantEnum
from ThreadManager.batch_update_service import BatchUpdateService
from ThreadManager.inactive_follow_buffer import InactiveFollowBuffer
from ThreadManager.reaction_batch_service import ReactionBatchService
from ThreadManager.thread_logic import ThreadLogic
from ThreadManager.views.visibility_view import ThreadVisibilityView
from core.redis_trend_service import RedisTrendService

import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from bot_main import MyBot


class ThreadManager(commands.Cog):
    """处理帖子同步、状态检测与评价"""

    def __init__(self, bot: "MyBot", session_factory: async_sessionmaker, config: dict):
        """初始化 ThreadManager，构建批量更新服务与业务逻辑处理器。"""
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.cache_service = bot.cache_service
        self.sync_service = bot.sync_service

        # 初始化后台更新服务
        update_interval = self.config.get("performance", {}).get(
            "batch_update_interval", 30
        )
        discovery_ignore = self.config.get("discovery", {}).get(
            "ignore_channel_ids", []
        )
        self.batch_update_service = BatchUpdateService(
            session_factory,
            sync_service=self.sync_service,
            interval=update_interval,
            ignore_channel_ids=discovery_ignore,
        )

        reaction_flush_interval = self.config.get("performance", {}).get(
            "reaction_flush_interval", 10
        )
        self.reaction_batch_service = ReactionBatchService(
            bot=self.bot,
            session_factory=session_factory,
            sync_service=self.sync_service,
            interval=reaction_flush_interval,
        )

        # 初始化非活跃关注 Redis 缓冲
        self.inactive_follow_buffer = InactiveFollowBuffer(
            session_factory,
            interval=update_interval,
        )

        # 实例化业务逻辑处理器
        self.logic = ThreadLogic(bot, session_factory, config, self.sync_service)
        logger.info("ThreadManager 模块已加载")

    async def cog_load(self):
        """当 Cog 加载时，启动后台任务，并注册持久化视图。"""
        self.batch_update_service.start()
        self.reaction_batch_service.start()
        self.inactive_follow_buffer.start()
        # 注册可见性切换的持久化视图
        self.bot.add_view(ThreadVisibilityView(self.bot, self.session_factory))

    async def cog_unload(self):
        """当 Cog 卸载时，确保所有数据都被写入。"""
        await self.batch_update_service.stop()
        await self.reaction_batch_service.stop()
        await self.inactive_follow_buffer.stop()

    def is_channel_indexed(self, channel_id: int) -> bool:
        """检查频道是否已索引"""
        return self.cache_service.is_channel_indexed(channel_id)

    # ---------------------------------------------------------
    # 事件监听器
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """新帖子创建时：同步索引并自动让贴主关注。"""
        if self.is_channel_indexed(channel_id=thread.parent_id):
            # 延时 5s 再进行同步。减小请求失败概率
            await asyncio.sleep(5)
            modified = await self.logic.apply_mutex_tag_rules(thread)
            if not modified:
                await self.sync_service.sync_thread(thread=thread)

            # 自动关注
            if thread.owner_id and (not thread.owner.bot if thread.owner else True):
                async with self.session_factory() as session:
                    follow_service = ThreadFollowRepository(session)
                    await follow_service.add_follow(
                        user_id=thread.owner_id,
                        thread_id=thread.id,
                        auto_view=False,  # 贴主发布时不标记为已查看
                    )

    @commands.Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember):
        """用户加入帖子时：自动关注并标记为已查看。"""
        try:
            thread = member.thread
            if not thread or not self.is_channel_indexed(thread.parent_id):
                return

            # 优先从本地服务器缓存获取，如果没有则从全局用户缓存获取
            user = thread.guild.get_member(member.id) or self.bot.get_user(member.id)

            # 如果缓存里能找到这个用户，并且它是机器人，则跳过
            if user and user.bot:
                return

            async with self.session_factory() as session:
                follow_service = ThreadFollowRepository(session)
                # 用户主动加入时，标记为已查看
                await follow_service.add_follow(
                    user_id=member.id, thread_id=thread.id, auto_view=True
                )
        except Exception as e:
            logger.error(f"用户加入帖子自动关注失败: {e}", exc_info=True)

    # ---------------------------------------------------------
    # 取消关注处理（公共逻辑 + 两个事件入口）
    # ---------------------------------------------------------

    async def _process_removed_members(
        self,
        thread_id: int,
        parent_id: int,
        guild: discord.Guild,
        removed_member_ids: list[int],
    ) -> None:
        """遍历被移除的帖子成员，写入 Redis 缓冲等待批量标记 inactive。"""
        for user_id in removed_member_ids:
            user = guild.get_member(user_id) or self.bot.get_user(user_id)
            if user and user.bot:
                continue

            await self.inactive_follow_buffer.add(thread_id=thread_id, user_id=user_id)

    @commands.Cog.listener()
    async def on_raw_thread_member_remove(
        self, payload: discord.RawThreadMembersUpdate
    ):
        """成员被移出帖子时：将关注标记为过去关注（经 Redis 缓冲批量写入 DB）。

        使用 raw 事件而非高级事件 on_thread_member_remove：
        - discord.py 的高级事件仅在 ThreadMember 对象存在于本地 thread._members 缓存时派发
        - Bot 重启后缓存清空，高级事件可能静默丢失
        - raw 事件始终派发（只要 guild 和 thread 在 discord.py 缓存中），更可靠
        """
        try:
            removed_member_ids = [
                int(uid) for uid in payload.data.get("removed_member_ids", [])
            ]
            if not removed_member_ids:
                return

            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return

            # 获取 parent_id（论坛频道 ID）：优先从 guild 缓存拿，没有则回退 DB
            thread = guild.get_thread(payload.thread_id)
            if thread is not None:
                parent_id = thread.parent_id
            else:
                async with self.session_factory() as session:
                    repo = ThreadRepository(session)
                    channel_id = await repo.get_thread_channel_id(payload.thread_id)
                if channel_id is None:
                    return
                parent_id = channel_id

            if not self.is_channel_indexed(parent_id):
                return

            await self._process_removed_members(
                thread_id=payload.thread_id,
                parent_id=parent_id,
                guild=guild,
                removed_member_ids=removed_member_ids,
            )
        except Exception as e:
            logger.error(f"处理 raw 成员移除事件失败: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        """帖子标签或名称变更时：应用互斥规则并触发同步。"""
        if self.is_channel_indexed(channel_id=after.parent_id) and (
            before.applied_tags != after.applied_tags or before.name != after.name
        ):
            modified = await self.logic.apply_mutex_tag_rules(after)
            if not modified:
                await self.sync_service.sync_thread(thread=after)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        """当整个 Thread 被从 Discord 删除时触发"""
        if self.is_channel_indexed(thread.parent_id):
            await self.logic.delete_thread_permanently(thread.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """新消息发送时：将帖子的回复计数和活跃时间增量写入缓存。"""
        if (
            not message.guild
            or not isinstance(message.channel, discord.Thread)
            or message.author.bot
        ):
            return

        thread = message.channel
        if thread.id == message.id:
            return

        if self.is_channel_indexed(thread.parent_id):
            await self.batch_update_service.add_update(
                thread.id, message.created_at.replace(tzinfo=None)
            )

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        """消息编辑时：首楼编辑触发同步，普通回复刷新活跃时间。"""
        if not payload.guild_id:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread) and self.is_channel_indexed(
                channel.parent_id
            ):
                if payload.message_id == channel.id:
                    await self.sync_service.sync_thread(
                        thread=channel, fetch_if_incomplete=True
                    )
                else:
                    await self.batch_update_service.add_active_at_update(
                        channel.id,
                        datetime.datetime.now(datetime.timezone.utc).replace(
                            tzinfo=None
                        ),
                    )
        except Exception:
            logger.warning("处理消息编辑事件失败", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """消息删除时：首楼删除则隐藏帖子，普通回复则递减计数。"""
        if not payload.guild_id:
            return
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if isinstance(channel, discord.Thread) and self.is_channel_indexed(
                channel.parent_id
            ):
                # 如果首楼被删除，隐藏帖子，并在楼内发送公示视图
                if payload.message_id == channel.id:
                    await self.logic.handle_first_message_deletion(channel)
                else:
                    await self.batch_update_service.add_deletion(channel.id)
        except Exception:
            logger.warning("处理消息删除事件失败", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """反应添加时：更新帖子反应数，60 天内帖子同步记录趋势。"""
        if not payload.guild_id:
            return
        try:
            channel = self.bot.get_channel(payload.channel_id)
            # 只有对首楼消息的反应才更新统计，且需要该帖所在频道已索引
            if (
                isinstance(channel, discord.Thread)
                and self.is_channel_indexed(channel.parent_id)
                and payload.message_id == channel.id
            ):
                # 检查帖子创建时间
                if channel.created_at:
                    threshold = datetime.datetime.now(
                        datetime.timezone.utc
                    ) - datetime.timedelta(
                        days=ConstantEnum.STATISTICS_THRESHOLD_DAYS.value
                    )
                    if channel.created_at >= threshold:
                        # 只有 60 天内创建的帖子才记录点赞飙升
                        # 检查是否在广场推荐忽略频道列表中
                        discovery_ignore = self.config.get("discovery", {}).get(
                            "ignore_channel_ids", []
                        )
                        if channel.parent_id not in discovery_ignore:
                            await RedisTrendService().record_increment(
                                "reaction",
                                channel.id,
                                channel.parent_id,
                                count=1,
                            )

                await self.reaction_batch_service.add_update(channel.id)
        except Exception:
            logger.warning("处理反应添加事件失败", exc_info=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """反应移除时：更新帖子反应数。"""
        if not payload.guild_id:
            return
        try:
            channel = self.bot.get_channel(payload.channel_id)
            if (
                isinstance(channel, discord.Thread)
                and self.is_channel_indexed(channel.parent_id)
                and payload.message_id == channel.id
            ):
                await self.reaction_batch_service.add_update(channel.id)
        except Exception:
            logger.warning("处理反应移除事件失败", exc_info=True)

    # ---------------------------------------------------------
    # 指令区
    # ---------------------------------------------------------
    # @app_commands.command(name="发布更新",
    #                       description="发布帖子更新（仅贴主可用）")
    # @app_commands.describe(消息链接="更新消息的Discord链接")
    async def publish_update(self, interaction: discord.Interaction, 消息链接: str):
        """贴主发布帖子更新公告。"""
        await safe_defer(interaction)
        try:
            if not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send(
                    "❌ 此命令只能在帖子中使用", ephemeral=True
                )
                return

            thread = interaction.channel
            if thread.owner_id != interaction.user.id:
                await interaction.followup.send(
                    "❌ 只有贴主才能发布更新", ephemeral=True
                )
                return

            await self.logic.process_publish_update(interaction, thread, 消息链接)
        except Exception:
            logger.error("发布更新命令执行失败", exc_info=True)
            await interaction.followup.send(
                "❌ 发生内部错误，请稍后重试", ephemeral=True
            )

    # @app_commands.command(
    #     name="标签评价", description="对当前帖子的标签进行评价（赞或踩）"
    # )
    async def tag_rate(self, interaction: discord.Interaction):
        """旧标签评价入口已停用，不再写入原生投票。"""
        await interaction.response.send_message(
            "DC 原生标签为只读，不再支持投票。", ephemeral=True
        )
