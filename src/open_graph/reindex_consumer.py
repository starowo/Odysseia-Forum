from __future__ import annotations

import asyncio
import logging

from core.sync_service import SyncService
from open_graph.reindex_queue import OpenGraphReindexQueue


logger = logging.getLogger(__name__)


class OpenGraphReindexConsumer:
    """在 Bot 进程消费 OG 重索引任务。"""

    def __init__(
        self,
        sync_service: SyncService,
        reindex_queue: OpenGraphReindexQueue,
    ):
        self.sync_service = sync_service
        self.reindex_queue = reindex_queue
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """启动后台消费循环。"""
        # 生命周期可能重复调用 start，已有活跃任务时保持幂等
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """取消后台消费循环。"""
        if self._task is None:
            return
        # 取消正在进行的任务时不写结果，pending 会在五分钟后自然过期
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _consume_loop(self) -> None:
        """持续消费任务，并在同步完成后写入持久化结果。"""
        while True:
            try:
                # BRPOP 带超时，确保关闭时消费循环能够及时响应取消
                job = await self.reindex_queue.pop_job()
                if not job:
                    continue
                await self._process_job(job["job_id"], job["thread_id"])
            except asyncio.CancelledError:
                # 取消属于正常生命周期信号，必须继续向上传播
                raise
            except Exception:
                # Redis 短暂故障时退避一秒，避免无间隔错误循环
                logger.exception("OG 重索引消费循环发生错误")
                await asyncio.sleep(1)

    async def _process_job(self, job_id: str, thread_id: int) -> None:
        """执行单个同步任务并写入脱敏结果。"""
        try:
            # SyncService 只有在帖子数据库事务提交成功后才返回 success
            result = await self.sync_service.sync_thread(thread_id, priority=5)
        except Exception:
            # 结果仅记录稳定失败码，不把异常详情、Token 或 URL 写入 Redis
            logger.exception(
                "OG 帖子重索引发生未处理错误",
                extra={"thread_id": thread_id},
            )
            await self.reindex_queue.finish_failure(
                job_id, thread_id, "unexpected_sync_failure"
            )
            return

        # 成功收尾会原子写 result、设置一小时 cooldown 并清理 pending
        if result.success:
            await self.reindex_queue.finish_success(job_id, thread_id)
            return
        # 失败不设置 cooldown，使后续请求可在 pending 清理后立即重试
        logger.warning(
            "OG 重索引失败",
            extra={
                "thread_id": thread_id,
                "job_id": job_id,
                "error_code": result.error_code or "sync_failed",
            },
        )
        await self.reindex_queue.finish_failure(
            job_id, thread_id, result.error_code or "sync_failed"
        )
