import logging
import random
from asyncio import sleep
from typing import List

from discord.ext import commands, tasks
from sqlalchemy.ext.asyncio import async_sessionmaker

from auditor.repository import AuditorRepository
from core.sync_service import SyncService
from shared.api_scheduler import APIScheduler

logger = logging.getLogger(__name__)


class Auditor(commands.Cog):
    """
    负责后台数据审计的 Cog

    这个 Cog 包含一个后台循环任务，该任务会定期执行完整的审计周期。
    在每个周期开始时，它会从数据库获取所有已索引的帖子ID，然后以非常低的速率
    将它们逐一提交给 API 调度器进行数据同步。这确保了本地数据与 Discord 的数据最终一致
    """

    def __init__(
        self,
        bot: commands.Bot,
        session_factory: async_sessionmaker,
        api_scheduler: APIScheduler,
        sync_service: SyncService,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.api_scheduler = api_scheduler
        self.sync_service = sync_service
        self.audit_queue: List[int] = []
        logger.info("Auditor 模块已加载")

    async def cog_load(self):
        """当 Cog 加载时，启动后台审计循环。"""
        self.audit_loop.start()
        self.cleanup_loop.start()

    async def cog_unload(self):
        """当 Cog 卸载时，取消后台审计循环。"""
        self.audit_loop.cancel()
        self.cleanup_loop.cancel()

    async def _reload_audit_queue(self):
        """
        从数据库重新加载需要审计的帖子 ID 列表。

        它会获取所有帖子的ID，并随机打乱顺序，以避免每次都从相同的帖子开始审计。
        """
        logger.debug("正在从数据库重新加载审计队列...")
        async with self.session_factory() as session:
            repo = AuditorRepository(session)
            self.audit_queue = await repo.get_all_thread_ids()
            random.shuffle(self.audit_queue)
        logger.debug(f"审计队列加载完成，共 {len(self.audit_queue)} 个帖子需要审计。")

    @tasks.loop(seconds=60)
    async def audit_loop(self):
        """
        主审计循环。

        这个循环负责执行一个完整的审计周期。它会先加载所有帖子ID，然后逐一处理。
        处理完所有帖子后，会等待一段时间，再开始下一个周期。
        """
        try:
            logger.debug("开始新一轮的后台数据审计周期...")
            await self._reload_audit_queue()

            if not self.audit_queue:
                logger.debug("没有需要审计的帖子，本轮审计周期跳过。")
            else:
                for thread_id in self.audit_queue:
                    if self.audit_loop.is_being_cancelled():
                        logger.info("审计循环被中断。")
                        break

                    await self.api_scheduler.submit(
                        coro_factory=lambda tid=thread_id: self.sync_service.sync_thread(
                            tid
                        ),
                        priority=10,
                    )
                    await sleep(4)

                if not self.audit_loop.is_being_cancelled():
                    logger.debug(
                        f"本轮 {len(self.audit_queue)} 个帖子的审计任务已全部提交。"
                    )

        except Exception as e:
            logger.error(f"审计循环发生严重错误: {e}", exc_info=True)
        finally:
            if not self.audit_loop.is_being_cancelled():
                logger.debug("本轮审计周期完成，将在1分钟后开始下一轮。")
                await sleep(60)

    @tasks.loop(hours=6)
    async def cleanup_loop(self):
        """定期清理那些被多次确认找不到的帖子记录。"""
        try:
            logger.info("开始执行幽灵数据清理任务...")
            async with self.session_factory() as session:
                repo = AuditorRepository(session)
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
