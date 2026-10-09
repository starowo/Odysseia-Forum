"""批量更新服务：将回复计数和活跃时间缓存在内存中，定时批量写入数据库。"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select

from core.sync_service import SyncService
from core.thread_repository import ThreadRepository
from models import Thread
from shared.database import is_deadlock_error
from shared.enum import ConstantEnum
from dto.update_data import UpdateData
from core.redis_trend_service import RedisTrendService

logger = logging.getLogger(__name__)

# 数据结构: {thread_id: {"increment": count, "last_active_at": datetime_obj}}
UpdatePayload = dict[int, UpdateData]


class BatchUpdateService:
    """负责批量更新帖子回复数和活跃时间的服务。

    数据分批写入，每批独立提交。即使一批死锁，其他批次不受影响，
    失败批次退回 pending_updates 等待下次重试，避免数据丢失。
    """

    BATCH_SIZE = 200

    def __init__(
        self,
        session_factory: async_sessionmaker,
        sync_service: SyncService,
        interval: int = 30,
        ignore_channel_ids: Optional[List[int]] = None,
    ):
        self.session_factory = session_factory
        self.sync_service = sync_service
        self.interval = interval  # 每隔多少秒写入一次数据库
        self.ignore_channel_ids = ignore_channel_ids or []

        # 待处理的更新
        self.pending_updates: defaultdict[int, UpdateData] = defaultdict(
            lambda: {"increment": 0, "last_active_at": None}
        )

        # asyncio.Lock 用于保证并发安全
        self.lock = asyncio.Lock()

        self._task: asyncio.Task | None = None
        logger.debug("BatchUpdateService 已初始化。")

    def start(self):
        """启动后台的批量写入任务。"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
            logger.debug(f"批量更新后台任务已启动，每 {self.interval} 秒执行一次。")

    async def stop(self):
        """停止后台任务并执行最后一次数据刷新。"""
        if self._task and not self._task.done():
            self._task.cancel()

        logger.debug("正在执行最后的批量数据刷新...")
        await self.flush_to_db()
        logger.debug("最后的批量数据刷新完成。")

    async def add_update(self, thread_id: int, message_time: datetime):
        """
        添加一次新消息更新到内存队列中。
        """
        async with self.lock:
            self.pending_updates[thread_id]["increment"] += 1
            self.pending_updates[thread_id]["last_active_at"] = message_time

    async def add_deletion(self, thread_id: int):
        """
        添加一次消息删除更新到内存队列中。
        """
        async with self.lock:
            self.pending_updates[thread_id]["increment"] -= 1

    async def add_active_at_update(self, thread_id: int, active_time: datetime):
        """
        仅更新帖子的活跃时间，不增加回复计数。
        用于消息编辑等不产生新回复但需要刷新活跃度的场景。
        """
        async with self.lock:
            data = self.pending_updates[thread_id]
            if data["last_active_at"] is None or active_time > data["last_active_at"]:
                data["last_active_at"] = active_time

    async def flush_to_db(self):
        """将内存中的所有待处理更新分批写入数据库，并处理幽灵数据。"""
        async with self.lock:
            if not self.pending_updates:
                return
            updates_to_process = self.pending_updates.copy()
            self.pending_updates.clear()

        all_ids = list(updates_to_process.keys())
        intended_count = len(all_ids)
        logger.debug(f"准备将 {intended_count} 个帖子的更新分批写入数据库。")

        # 分批写入
        failed_batches: list[dict] = []
        successful_ids: list[int] = []

        for batch_idx in range(0, len(all_ids), self.BATCH_SIZE):
            batch_ids = all_ids[batch_idx : batch_idx + self.BATCH_SIZE]
            batch = {tid: updates_to_process[tid] for tid in batch_ids}
            success = await self._flush_one_batch(batch)
            if success:
                successful_ids.extend(batch_ids)
            else:
                failed_batches.append(batch)

        # 失败批次退回 pending_updates
        if failed_batches:
            failed_count = sum(len(b) for b in failed_batches)
            failed_id_sample = list(failed_batches[0].keys())[:10]
            logger.warning(
                f"批量更新：{failed_count} 个帖子在重试后仍然失败 "
                f"(ID 样本: {failed_id_sample})，退回队列等待下次重试。"
            )
            async with self.lock:
                for batch in failed_batches:
                    for tid, data in batch.items():
                        existing = self.pending_updates[tid]
                        existing["increment"] += data["increment"]
                        if data["last_active_at"] is not None and (
                            existing["last_active_at"] is None
                            or data["last_active_at"] > existing["last_active_at"]
                        ):
                            existing["last_active_at"] = data["last_active_at"]

        # 以下所有后处理仅针对成功批次
        if not successful_ids:
            return

        try:
            # 筛选出 60 天内创建的帖子 ID
            threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                days=ConstantEnum.STATISTICS_THRESHOLD_DAYS.value
            )

            async with self.session_factory() as session:
                stmt = select(Thread.thread_id, Thread.channel_id).where(
                    Thread.thread_id.in_(successful_ids),  # type: ignore
                    Thread.created_at >= threshold,
                )
                if self.ignore_channel_ids:
                    stmt = stmt.where(
                        Thread.channel_id.notin_(self.ignore_channel_ids)  # type: ignore
                    )
                valid_result = await session.execute(stmt)
                valid_channel_by_thread = {
                    int(thread_id): int(channel_id)
                    for thread_id, channel_id in valid_result.all()
                }

            # 将讨论数的增量同步至趋势服务 (redis) (仅针对有效ID)
            trend_service = RedisTrendService()
            for tid in successful_ids:
                channel_id = valid_channel_by_thread.get(tid)
                if channel_id and updates_to_process[tid]["increment"] > 0:
                    await trend_service.record_increment(
                        "reply",
                        tid,
                        channel_id,
                        count=updates_to_process[tid]["increment"],
                    )

            # 处理可能不存在于数据库里的数据
            async with self.session_factory() as session:
                repo = ThreadRepository(session)
                existing_ids = await repo.get_existing_thread_ids(successful_ids)

            ghost_ids = set(successful_ids) - set(existing_ids)
            if ghost_ids:
                logger.info(
                    f"批量更新消息数时发现 {len(ghost_ids)} 条幽灵数据，将触发数据补录。"
                )
                logger.info(f"需要补录的帖子ID: {list(ghost_ids)}")
                for thread_id in ghost_ids:
                    asyncio.create_task(
                        self.sync_service.sync_thread(thread_id, priority=10)
                    )

            logger.debug(
                f"批量更新成功：{len(successful_ids)}/{intended_count} 个帖子已写入。"
            )

        except Exception as e:
            logger.error("批量更新后处理（Redis/幽灵检测）发生错误。", exc_info=e)

    async def _flush_one_batch(self, batch: dict[int, UpdateData]) -> bool:
        """
        尝试将一批更新写入数据库，支持死锁自动重试。

        Returns:
            True 表示写入成功，False 表示重试耗尽。
        """
        for attempt in range(3):
            async with self.session_factory() as session:
                try:
                    repo = ThreadRepository(session)
                    await repo.batch_update_thread_activity(batch)
                    await session.commit()
                    return True

                except DBAPIError as e:
                    await session.rollback()
                    if is_deadlock_error(e) and attempt < 2:
                        backoff = 0.1 * (2**attempt)
                        logger.debug(
                            f"批量更新遇到死锁，{backoff}s 后重试 "
                            f"(第 {attempt + 1}/3 次)。"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    logger.error(
                        f"批量更新批次写入失败 (尝试 {attempt + 1}/3)："
                        f"batch 大小={len(batch)}，错误: {e}"
                    )

                except Exception as e:
                    await session.rollback()
                    logger.error(f"批量更新批次写入失败 (非数据库错误): {e}")
                    break

        return False

    async def _run_loop(self):
        """后台任务的主循环。"""
        while True:
            try:
                await asyncio.sleep(self.interval)
                await self.flush_to_db()
            except asyncio.CancelledError:
                logger.info("批量更新后台任务已被取消。")
                break
            except Exception as e:
                logger.error("批量更新后台循环发生错误。", exc_info=e)
