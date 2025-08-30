import discord
import datetime
import logging
from typing import Coroutine, Union, TYPE_CHECKING
from sqlalchemy.ext.asyncio import async_sessionmaker

# 导入 ThreadManagerRepository，因为 sync_thread 方法会用到它
from src.ThreadManager.repository import ThreadManagerRepository

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)

class SyncService:
    """
    负责将 Discord 帖子数据同步到数据库的服务。
    包含从 Discord API 获取数据和执行数据库操作的逻辑。
    """
    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
    ):
        self.bot = bot
        self.session_factory = session_factory

    @staticmethod
    async def _fetch_message_wrapper(fetch_coro: Coroutine) -> discord.Message | None:
        """
        包装一个获取消息的协程
        如果协程成功，返回消息对象；如果抛出 NotFound，返回 None。
        """
        try:
            return await fetch_coro
        except discord.NotFound:
            return None

    async def sync_thread(
        self,
        thread: Union[discord.Thread, int],
        priority: int = 10,
        *,
        fetch_if_incomplete: bool = False,
    ):
        """
        同步一个帖子的数据到数据库，包括其标签。
        该方法可以接受一个完整的帖子对象，或者一个帖子ID。
        :param thread: 要同步的帖子对象或帖子ID。
        :param priority: 此操作的API调用优先级。
        :param fetch_if_incomplete: 如果为True，则强制从API获取最新的帖子对象，用于处理可能不完整的对象。
        """
        # 如果传入的是帖子ID（来自审计模块），则先通过API获取帖子对象
        if isinstance(thread, int):
            thread_id = thread
            try:
                fetched_channel = await self.bot.api_scheduler.submit(
                    coro_factory=lambda: self.bot.fetch_channel(thread_id),
                    priority=priority,
                )
                if not isinstance(fetched_channel, discord.Thread):
                    logger.warning(
                        f"sync_thread: 获取到的 channel {thread_id} 不是一个帖子，已将其从索引中删除。"
                    )
                    async with self.session_factory() as session:
                        repo = ThreadManagerRepository(session=session)
                        await repo.delete_thread_index(thread_id=thread_id)
                    return
                thread = fetched_channel
            except discord.NotFound:
                logger.warning(
                    f"sync_thread: 无法找到帖子 {thread_id}，可能已被删除。将从数据库中移除。"
                )
                async with self.session_factory() as session:
                    repo = ThreadManagerRepository(session=session)
                    await repo.delete_thread_index(thread_id=thread_id)
                return
            except Exception as e:
                logger.error(
                    f"sync_thread: 通过ID {thread_id} 获取帖子时发生未知错误: {e}",
                    exc_info=True,
                )
                return

        # 如果需要，强制从API获取最新的帖子对象
        elif fetch_if_incomplete:
            try:
                # 确保 thread 是对象而不是 int
                thread_id = thread.id if isinstance(thread, discord.Thread) else thread
                thread = await self.bot.api_scheduler.submit(
                    coro_factory=lambda: self.bot.fetch_channel(thread_id),
                    priority=priority,
                )
            except discord.NotFound:
                logger.warning(
                    f"sync_thread (fetch_if_incomplete): 无法找到帖子 {thread.id}，可能已被删除。"
                )
                async with self.session_factory() as session:
                    repo = ThreadManagerRepository(session=session)
                    await repo.delete_thread_index(thread_id=thread.id)
                return
        assert isinstance(thread, discord.Thread)

        tags_data = {t.id: t.name for t in thread.applied_tags or []}

        excerpt = ""
        thumbnail_url = ""
        reaction_count = 0

        # 创建原始的获取消息的协程，并用包装器包裹它
        first_msg = await self.bot.api_scheduler.submit(
            coro_factory=lambda: self._fetch_message_wrapper(thread.fetch_message(thread.id)),
            priority=priority,
        )

        # 如果返回 None，说明帖子已被删除，记录日志并从数据库删除
        if first_msg is None:
            logger.debug(
                f"无法获取帖子 {thread.id} 的首楼消息，其可能已被删除\n已将其从索引中删除"
            )
            async with self.session_factory() as session:
                repo = ThreadManagerRepository(session=session)
                await repo.delete_thread_index(thread_id=thread.id)
            return

        # 消息获取成功，但解析内容时可能出错
        try:
            excerpt = first_msg.content
            if first_msg.attachments:
                thumbnail_url = first_msg.attachments[0].url
            reaction_count = (
                max([r.count for r in first_msg.reactions])
                if first_msg.reactions
                else 0
            )
        except Exception:
            logger.error(f"同步帖子 {thread.id} 时解析首楼消息内容失败", exc_info=True)

        thread_data = {
            "thread_id": thread.id,
            "channel_id": thread.parent_id,
            "title": thread.name,
            "author_id": thread.owner_id or 0,
            "created_at": thread.created_at,
            "last_active_at": discord.utils.snowflake_time(thread.last_message_id)
            if thread.last_message_id
            else thread.created_at,
            "reaction_count": reaction_count,
            "reply_count": thread.message_count,
            "first_message_excerpt": excerpt,
            "thumbnail_url": thumbnail_url,
        }

        async with self.session_factory() as session:
            repo = ThreadManagerRepository(session=session)
            await repo.add_or_update_thread_with_tags(
                thread_data=thread_data, tags_data=tags_data
            )