import logging
from typing import TYPE_CHECKING, List

from discord.ext import commands
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.thread_repository import ThreadRepository

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class StatsListenerCog(commands.Cog):
    """监听并异步处理统计数据更新（如帖子收藏数去重累加）"""

    def __init__(self, bot: "MyBot", session_factory: async_sessionmaker):
        self.bot = bot
        self.session_factory = session_factory

    @commands.Cog.listener()
    async def on_thread_collection_updated(self, thread_ids: List[int], delta: int):
        """
        处理帖子收藏数更新事件。
        该事件由业务层抛出，传入的 thread_ids 已完成"用户维度去重"判定。
        """
        if not thread_ids or delta == 0:
            return

        try:
            async with self.session_factory() as session:
                thread_repo = ThreadRepository(session)
                await thread_repo.update_collection_counts(thread_ids, delta)

            logger.debug(
                f"已异步更新 {len(thread_ids)} 个帖子的收藏数，变化量: {delta}"
            )
        except Exception as e:
            logger.error(f"异步更新帖子收藏数失败: {e}", exc_info=True)
