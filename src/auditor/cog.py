import logging
import random
from asyncio import sleep
from typing import TYPE_CHECKING

from discord.ext import commands, tasks
from sqlalchemy.ext.asyncio import async_sessionmaker

from auditor.auditor_service import AuditorService


if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class Auditor(commands.Cog):
    """
    负责后台数据审计的 Cog

    这个 Cog 包含一个后台循环任务，该任务会定期执行完整的审计周期。
    使用自增主键 ``id`` 做 keyset 分页，逐批从数据库加载帖子 ID，
    避免一次性加载全表带来的内存压力。
    """

    AUDIT_BATCH_SIZE = 500

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.api_scheduler = bot.api_scheduler
        self.sync_service = bot.sync_service
        self._audit_cursor: int = 0
        logger.info("Auditor 模块已加载")

    async def cog_load(self):
        """当 Cog 加载时，启动后台审计循环。"""
        self.audit_loop.start()
        self.cleanup_loop.start()

    async def cog_unload(self):
        """当 Cog 卸载时，取消后台审计循环。"""
        self.audit_loop.cancel()
        self.cleanup_loop.cancel()

    @tasks.loop(seconds=0)
    async def audit_loop(self):
        """
        主审计循环（keyset 分页模式）。

        每轮拉一批、处理一批、推进游标，直到扫完整张表后重置游标等待下一轮。
        使用自增主键 ``id`` 作为游标，保证新插入的行不会在本轮遗漏。
        """
        try:
            if self._audit_cursor == 0:
                logger.debug("开始新一轮的后台数据审计周期...")

            async with self.session_factory() as session:
                repo = AuditorService(session)
                batch = await repo.get_thread_ids_batch(
                    cursor=self._audit_cursor,
                    batch_size=self.AUDIT_BATCH_SIZE,
                )

            if not batch:
                logger.debug("本轮所有帖子已审计完毕，准备开始下一轮。")
                self._audit_cursor = 0
                return

            thread_ids = [tid for _, tid in batch]
            random.shuffle(thread_ids)

            for thread_id in thread_ids:
                if self.audit_loop.is_being_cancelled():
                    logger.info("审计循环被中断。")
                    return

                await self.api_scheduler.submit(
                    coro_factory=lambda tid=thread_id: self.sync_service.sync_thread(
                        tid
                    ),
                    priority=10,
                )
                await sleep(3)

            self._audit_cursor = batch[-1][0]
            logger.debug(
                f"批次处理完成，cursor -> {self._audit_cursor}，共 {len(batch)} 条"
            )

        except Exception as e:
            logger.error(f"审计循环发生严重错误: {e}", exc_info=True)
        finally:
            if not self.audit_loop.is_being_cancelled() and self._audit_cursor == 0:  # type: ignore
                logger.debug("本轮审计周期完成，将在1分钟后开始下一轮。")
                await sleep(60)

    @tasks.loop(hours=6)
    async def cleanup_loop(self):
        """定期清理那些被多次确认找不到的帖子记录。"""
        try:
            logger.info("开始执行幽灵数据清理任务...")
            async with self.session_factory() as session:
                repo = AuditorService(session)
                # 清理连续5次都找不到的帖子
                deleted_count = await repo.delete_stale_threads(threshold=5)

            if deleted_count > 0:
                logger.info(f"幽灵数据清理完成，共删除了 {deleted_count} 条记录。")
            else:
                logger.debug("幽灵数据清理完成，没有需要删除的记录。")

        except Exception as e:
            logger.error(f"幽灵数据清理任务发生严重错误: {e}", exc_info=True)

    @audit_loop.before_loop
    @cleanup_loop.before_loop
    async def before_loops(self):
        """在循环开始前，等待机器人完全准备就绪。"""
        await self.bot.wait_until_ready()
