"""反应数去重批量服务：收集需要更新 reaction count 的帖子 ID，定时去重后批量处理。"""

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from core.thread_repository import ThreadRepository

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class ReactionBatchService:
    """去重反应数更新：同一帖子在 interval 秒内的多次 reaction 只触发一次 fetch+write。"""

    def __init__(self, bot: "MyBot", session_factory, sync_service, interval: int = 10):
        self.bot = bot
        self.session_factory = session_factory
        self.sync_service = sync_service
        self.interval = interval

        self._pending: set[int] = (
            set()
        )  # set 自动去重，同一帖子多次 reaction 只处理一次
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(4)  # 限制并发 Discord API 请求数
        self._task: asyncio.Task | None = None
        logger.debug("ReactionBatchService 已初始化，interval=%ds", interval)

    def start(self):
        """启动后台定时刷新任务。"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
            logger.debug(
                "反应数批量更新后台任务已启动，每 %d 秒执行一次。", self.interval
            )

    async def stop(self):
        """取消后台任务并执行最后一次刷新，确保数据不丢失。"""
        if self._task and not self._task.done():
            self._task.cancel()
        logger.debug("正在执行最后的反应数批量刷新...")
        await self.flush()
        logger.debug("最后的反应数批量刷新完成。")

    async def add_update(self, thread_id: int):
        """将帖子 ID 加入待处理集合，同一 interval 内重复添加自动去重。"""
        async with self._lock:
            self._pending.add(thread_id)

    async def flush(self):
        """取出当前所有待处理 ID 并批量更新反应数到数据库。"""
        async with self._lock:
            if not self._pending:
                return
            batch = self._pending.copy()
            self._pending.clear()

        logger.debug("准备更新 %d 个帖子的反应数。", len(batch))

        async def _process_one(thread_id: int):
            channel = self.bot.get_channel(thread_id)
            if not isinstance(channel, discord.Thread):
                return
            try:
                first_msg = await channel.get_partial_message(thread_id).fetch()
                # 取最高单反应计数作为帖子的 reaction 指标（标签投票场景下即最高票数）
                reaction_count = (
                    max(r.count for r in first_msg.reactions)
                    if first_msg.reactions
                    else 0
                )
                async with self.session_factory() as session:
                    repo = ThreadRepository(session)
                    update_succeeded = await repo.update_thread_reaction_count(
                        thread_id, reaction_count
                    )
                    await session.commit()
                    if not update_succeeded:
                        logger.warning(
                            "帖子 %d 反应数更新失败，触发同步补录。", thread_id
                        )
                        await self.sync_service.sync_thread(thread=channel)
            except discord.NotFound:
                # 帖子或消息在排期中被删除，无需处理
                pass
            except Exception:
                logger.warning("更新反应数失败 (帖子ID: %d)", thread_id, exc_info=True)

        async def _with_semaphore(thread_id: int):
            async with self._semaphore:
                await _process_one(thread_id)

        tasks = [_with_semaphore(tid) for tid in batch]
        await asyncio.gather(*tasks)

    async def _run_loop(self):
        """定时循环：每隔 interval 秒执行一次 flush。"""
        while True:
            try:
                await asyncio.sleep(self.interval)
                await self.flush()
            except asyncio.CancelledError:
                logger.info("反应数批量更新后台任务已被取消。")
                break
            except Exception:
                logger.error("反应数批量更新后台循环发生错误。", exc_info=True)
