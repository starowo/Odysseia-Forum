import asyncio
import logging
from collections import Counter
from typing import TYPE_CHECKING

from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import update

from models import BotConfig, Thread
from shared.enum.search_config_type import SearchConfigType

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class ImpressionCacheService:
    """
    处理帖子展示次数的内存缓存和定期数据库回写服务。
    """

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        flush_interval: int = 60,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.flush_interval = flush_interval  # 默认1分钟回写一次
        self._impression_cache = Counter()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._is_running = False

    def start(self):
        """启动后台定期回写任务。"""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._periodic_flush())
        logger.info(
            f"ImpressionCacheService 已启动，每 {self.flush_interval} 秒回写一次数据库。"
        )

    async def stop(self):
        """停止服务并执行最后一次回写。"""
        if not self._is_running:
            return
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ImpressionCacheService 正在停止，执行最后一次数据回写...")
        await self.flush_to_db()
        logger.info("最终数据回写完成。")

    async def _periodic_flush(self):
        """定期执行回写的后台任务。"""
        while self._is_running:
            await asyncio.sleep(self.flush_interval)
            logger.debug("开始定期回写展示次数...")
            await self.flush_to_db()

    async def increment(self, thread_ids: list[int]):
        """在内存中为帖子增加展示次数。"""
        async with self._lock:
            for thread_id in thread_ids:
                self._impression_cache[thread_id] += 1

    async def flush_to_db(self):
        """将内存中的缓存数据写入数据库。"""
        async with self._lock:
            if not self._impression_cache:
                return

            # 复制并清空缓存，以便在DB操作期间可以继续接收新的计数
            data_to_flush = self._impression_cache.copy()
            self._impression_cache.clear()

        total_increment = sum(data_to_flush.values())

        async with self.session_factory() as session:
            try:
                # 针对 SQLite 的批量更新
                # 使用 CASE 表达式来为不同的 thread_id 设置不同的增量值
                whens = {
                    tid: Thread.display_count + count
                    for tid, count in data_to_flush.items()
                }
                case_statement = case(
                    whens, value=Thread.id, else_=Thread.display_count
                )

                await session.execute(
                    update(Thread)
                    .where(Thread.id.in_(data_to_flush.keys()))  # type: ignore
                    .values(display_count=case_statement)
                )

                # 更新全局总展示次数 N
                await session.execute(
                    update(BotConfig)
                    .where(BotConfig.type == SearchConfigType.TOTAL_DISPLAY_COUNT)  # type: ignore
                    .values(
                        value_int=(
                            func.coalesce(BotConfig.value_int, 0) + total_increment
                        )
                    )
                )

                await session.commit()

                # 发布配置更新事件
                self.bot.dispatch("config_updated")

                logger.debug(
                    f"成功回写 {len(data_to_flush)} 个帖子的展示次数，总增量为 {total_increment}。"
                )
            except Exception as e:
                logger.error(f"回写展示次数到数据库失败: {e}", exc_info=True)
                # 失败后将数据还回缓存，下次重试
                async with self._lock:
                    self._impression_cache.update(data_to_flush)
                await session.rollback()
