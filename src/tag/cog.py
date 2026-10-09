from core.discord_tag_sync_service import DiscordTagSyncService
from dto.events.discord_tags_snapshot import DiscordTagsSnapshot
from models import Tag
from shared.time_utils import utc_now
from tag.tag_category_select import TagCategorySelect

import json
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from dto.events.tag_command import TagCommand
from core.tag_pool_cache_service import TagPoolCacheService
from shared.redis_client import RedisManager
from shared.tag_error import TagError
from tag.tag_runtime import create_tag_mediator
from tag.tag_worker import TagWorker

logger = logging.getLogger(__name__)


class TagCog(commands.Cog):
    """提供 BOT 标签管理命令与审核后台任务。"""

    def __init__(self, bot, session_factory, config):
        self.session_factory = session_factory
        self.bot = bot
        self.config = config
        self.worker = TagWorker(session_factory, config)
        # 独立测试或 Redis 尚未初始化时禁用缓存，标签主流程仍可访问数据库。
        try:
            redis = RedisManager.get_client()
        except RuntimeError:
            redis = None
        self.pool_cache = TagPoolCacheService(redis)
        self.mediator = create_tag_mediator(session_factory, config, redis)

    async def cog_load(self):
        """启动可恢复的审核和通知循环。"""
        self.bot.add_dynamic_items(TagCategorySelect)
        self.bot.event_mediator.register(DiscordTagsSnapshot, self.sync_snapshot)
        self.reconcile.start()
        self.expire.start()
        self.notify.start()

    async def cog_unload(self):
        """停止后台循环。"""
        self.reconcile.cancel()
        self.bot.remove_dynamic_items(TagCategorySelect)
        self.expire.cancel()
        self.notify.cancel()

    @tasks.loop(minutes=1)
    async def expire(self):
        """自动处理满七天申请。"""
        try:
            await self.worker.expire()
        except Exception:
            logger.exception("标签审核循环失败")

    @tasks.loop(seconds=5)
    async def notify(self):
        """逐条发送持久化通知。"""
        try:
            await self.worker.deliver(self.send_notice, self.send_lifecycle_notice)
        except Exception:
            logger.exception("标签通知循环失败")

    @notify.before_loop
    async def before_notify(self):
        """等待 BOT 连接完成。"""
        await self.bot.wait_until_ready()

    async def send_notice(self, proposal):
        """私信失败后在帖子提醒，书单和不可写帖子使用站内通知。"""
        frontend = self.config.get("auth", {}).get("frontend_url", "").rstrip("/")
        path = "threads" if proposal.target_type == "thread" else "booklists"
        frontend = f"{frontend}/{path}/{proposal.target_id}"
        message = (
            f"你有一条待审核的标签提议（申请 {proposal.id}，"
            f"{'帖子' if proposal.target_type == 'thread' else '书单'} {proposal.target_id}）。"
            f"请前往索引页审核；若未审核，将在提交满 7 天后将自动通过。 {frontend}"
        )
        try:
            user = self.bot.get_user(proposal.owner_id) or await self.bot.fetch_user(
                proposal.owner_id
            )
            await user.send(message)
            return True
        except (discord.Forbidden, discord.NotFound):
            pass
        if proposal.target_type == "thread":
            try:
                channel = self.bot.get_channel(
                    proposal.target_id
                ) or await self.bot.fetch_channel(proposal.target_id)
                await channel.send(
                    f"<@{proposal.owner_id}> 有新的标签提议待审核，请前往索引页处理。 {frontend}",
                    allowed_mentions=discord.AllowedMentions(
                        users=[discord.Object(proposal.owner_id)],
                        roles=False,
                        everyone=False,
                    ),
                )
                return True
            except (discord.Forbidden, discord.NotFound):
                pass
        return False

    async def sync_snapshot(self, event):
        """接收跨模块快照事件并持久化标签生命周期变化。"""
        async with self.session_factory() as session, session.begin():
            pool_changed = await DiscordTagSyncService(session).apply(event)
        if pool_changed:
            await self.pool_cache.invalidate()

    @tasks.loop(minutes=10)
    async def reconcile(self):
        """启动后及周期性读取完整频道快照，补偿离线事件。"""
        for channel_id in list(self.bot.cache_service.indexed_channels):
            try:
                observed_at = utc_now()
                channel = await self.bot.fetch_channel(channel_id)
                if isinstance(channel, discord.ForumChannel):
                    await self.bot.event_mediator.publish(
                        DiscordTagsSnapshot(
                            channel.id,
                            {t.id: t.name for t in channel.available_tags},
                            observed_at,
                        )
                    )
            except Exception:
                logger.exception(
                    "频道标签同步失败，保留已有数据 channel_id=%s", channel_id
                )

    @reconcile.before_loop
    async def before_reconcile(self):
        """等待连接完成再执行启动补偿。"""
        await self.bot.wait_until_ready()

    async def send_lifecycle_notice(self, task):
        """发送转换或分类冲突提醒，失败交由持久化任务重试。"""
        channel_id = self.config.get("banner", {}).get("review_thread_id")
        if not channel_id:
            raise RuntimeError("未配置 banner.review_thread_id")
        async with self.session_factory() as session:
            tag = await session.get(Tag, task.tag_id)
            if tag is None:
                return
            title = (
                "DC 标签已转为自定义标签，等待分类"
                if task.kind == "converted"
                else "标签同名或分类冲突，请通过标签合并预检处理"
            )
            message = f"{title}\n标签：{tag.name}（内部 ID：{tag.id}）"
            view = None
            if (
                task.kind == "converted"
                and tag.source == "custom"
                and tag.category is None
                and tag.deleted_at is None
            ):
                view = discord.ui.View(timeout=None)
                view.add_item(TagCategorySelect(tag.id))
        channel = await self.bot.fetch_channel(int(channel_id))
        await channel.send(
            message, view=view, allowed_mentions=discord.AllowedMentions.none()
        )

    @app_commands.command(
        name="tag_manage", description="BOT 管理员维护标签池，提交 JSON 管理命令"
    )
    async def tag_manage(self, interaction: discord.Interaction, payload: str):
        """使用与管理 API 相同的领域命令维护标签。"""
        await interaction.response.defer(ephemeral=True)
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError("管理命令必须是 JSON 对象")
            result = await self.mediator.request(
                TagCommand("manage", interaction.user.id, data)
            )
            await interaction.followup.send(
                json.dumps(result, ensure_ascii=False, default=str)[:1900],
                ephemeral=True,
            )
        except (TagError, ValueError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
