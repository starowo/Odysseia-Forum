import asyncio
import logging
from collections import Counter
from typing import TYPE_CHECKING

from sqlalchemy import case, func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import update

from models import BotConfig, Thread
from shared.database import is_deadlock_error
from shared.enum import SearchConfigType

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class ImpressionCacheService:
    """
    处理帖子展示次数的内存缓存和定期数据库回写服务。

    数据分批写入，每批独立提交。即使一批死锁，其他批次也不受影响，
    避免「失败→全部回填→更大批量→更易死锁」的正反馈循环。
    """

    BATCH_SIZE = 200

    def __init__(
        self,
        session_factory: async_sessionmaker,
        bot: "MyBot | None" = None,
        flush_interval: int = 180,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.flush_interval = flush_interval  # 默认3分钟回写一次
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
        """将内存中的缓存数据分批写入数据库。"""
        async with self._lock:
            if not self._impression_cache:
                return
            data_to_flush = self._impression_cache.copy()
            self._impression_cache.clear()

        total_increment = sum(data_to_flush.values())
        items = list(data_to_flush.items())
        failed_items: list[tuple[int, int]] = []

        for batch_idx in range(0, len(items), self.BATCH_SIZE):
            batch = dict(items[batch_idx : batch_idx + self.BATCH_SIZE])
            success = await self._flush_one_batch(batch)
            if not success:
                failed_items.extend(batch.items())

        # 仅失败的数据退回缓存（而非全部），打破雪球效应
        if failed_items:
            failed_count = len(failed_items)
            failed_ids = [tid for tid, _ in failed_items[:10]]
            logger.warning(
                f"展示次数回写：{failed_count} 个帖子在重试后仍然失败 "
                f"(ID 样本: {failed_ids})，退回缓存等待下次重试。"
            )
            async with self._lock:
                for tid, count in failed_items:
                    self._impression_cache[tid] += count

        # 仅使用成功批次的增量更新全局总展示次数
        failed_increment = sum(count for _, count in failed_items)
        successful_increment = total_increment - failed_increment
        if successful_increment > 0:
            await self._flush_bot_config(successful_increment)

        succeeded = len(items) - len(failed_items)
        if succeeded > 0:
            logger.debug(
                f"成功回写 {succeeded}/{len(items)} 个帖子的展示次数，"
                f"总增量为 {successful_increment}。"
            )

    async def _flush_one_batch(self, batch: dict[int, int]) -> bool:
        """
        尝试将一批数据写入数据库，支持死锁自动重试。

        Returns:
            True 表示写入成功，False 表示重试耗尽。
        """
        for attempt in range(3):
            async with self.session_factory() as session:
                try:
                    whens = {
                        tid: Thread.display_count + count
                        for tid, count in batch.items()
                    }
                    case_statement = case(
                        whens, value=Thread.id, else_=Thread.display_count
                    )

                    await session.execute(
                        update(Thread)
                        .where(Thread.id.in_(batch.keys()))  # type: ignore
                        .values(display_count=case_statement)
                    )
                    await session.commit()
                    return True

                except DBAPIError as e:
                    await session.rollback()
                    if is_deadlock_error(e) and attempt < 2:
                        backoff = 0.1 * (2**attempt)
                        logger.debug(
                            f"展示次数批次回写遇到死锁，{backoff}s 后重试 "
                            f"(第 {attempt + 1}/3 次)。"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    # 死锁重试耗尽或其他 DB 错误
                    logger.error(
                        f"展示次数批次回写失败 (尝试 {attempt + 1}/3)："
                        f"batch 大小={len(batch)}，错误: {e}"
                    )

                except Exception as e:
                    await session.rollback()
                    logger.error(f"展示次数批次回写失败 (非数据库错误): {e}")
                    break

        return False

    async def _flush_bot_config(self, increment: int):
        """更新全局总展示次数（独立事务，单行更新，不会死锁）。"""
        try:
            async with self.session_factory() as session:
                await session.execute(
                    update(BotConfig)
                    .where(BotConfig.type == SearchConfigType.TOTAL_DISPLAY_COUNT)  # type: ignore
                    .values(
                        value_int=(func.coalesce(BotConfig.value_int, 0) + increment)
                    )
                )
                await session.commit()
        except Exception as e:
            logger.error(f"更新全局总展示次数失败 (增量={increment}): {e}")
            return

        # 发布配置更新事件（仅 Bot 进程）
        if self.bot is not None:
            self.bot.dispatch("config_updated")
