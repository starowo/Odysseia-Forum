import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.sync_service import SyncService

from .thread_manager_service import ThreadManagerService
from .update_data_dto import UpdateData

logger = logging.getLogger(__name__)

# 数据结构: {thread_id: {"increment": count, "last_active_at": datetime_obj}}
UpdatePayload = dict[int, UpdateData]


class BatchUpdateService:
    """负责批量更新帖子回复数和活跃时间的服务。"""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        sync_service: SyncService,
        interval: int = 30,
    ):
        self.session_factory = session_factory
        self.sync_service = sync_service
        self.interval = interval  # 每隔多少秒写入一次数据库

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

    async def flush_to_db(self):
        """将内存中的所有待处理更新写入数据库，并处理幽灵数据。"""
        async with self.lock:
            if not self.pending_updates:
                return  # 如果没有更新，直接返回

            updates_to_process = self.pending_updates.copy()
            self.pending_updates.clear()

        intended_count = len(updates_to_process)
        logger.debug(f"准备将 {intended_count} 个帖子的更新写入数据库。")
        try:
            async with self.session_factory() as session:
                repo = ThreadManagerService(session)
                updated_count = await repo.batch_update_thread_activity(
                    updates_to_process
                )
                await session.commit()

            logger.debug(f"批量更新成功写入数据库，影响了 {updated_count} 行。")

            # 处理可能不存在于数据库里的数据
            if updated_count < intended_count:
                logger.info(
                    f"批量更新消息数时发现 {intended_count - updated_count} 条幽灵数据，"
                    "将触发数据补录。"
                )

                # 查询比对
                async with self.session_factory() as session:
                    repo = ThreadManagerService(session)
                    all_ids_in_batch = list(updates_to_process.keys())
                    existing_ids = await repo.get_existing_thread_ids(all_ids_in_batch)

                ghost_ids = set(all_ids_in_batch) - set(existing_ids)

                logger.info(f"需要补录的帖子ID: {list(ghost_ids)}")

                # 为每个帖子触发一次完整的同步，使用 create_task 在后台执行
                for thread_id in ghost_ids:
                    asyncio.create_task(
                        self.sync_service.sync_thread(thread_id, priority=10)
                    )

        except Exception as e:
            logger.error("批量更新写入数据库时发生严重错误！", exc_info=e)
            # todo: 可以在这里添加错误重试逻辑，例如将 updates_to_process 放回 self.pending_updates
            # 我想想，嗯

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
