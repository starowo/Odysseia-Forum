import logging
import random
from asyncio import sleep
from typing import TYPE_CHECKING, List

from discord.ext import commands, tasks
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.auditor.repository import AuditorRepository
from src.shared.api_scheduler import APIScheduler
from src.core.sync_service import SyncService

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

    async def cog_unload(self):
        """当 Cog 卸载时，取消后台审计循环。"""
        self.audit_loop.cancel()

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

    @tasks.loop(seconds=10)  # 机器人启动10秒后开始第一次循环
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
                    # 在处理每个任务前检查循环是否已被取消
                    if self.audit_loop.is_being_cancelled():
                        logger.info("审计循环被中断。")
                        break

                    # logger.debug(f"正在提交帖子 {thread_id} 的审计任务。")
                    # 使用最低优先级(10)来调度同步任务，确保不影响用户交互
                    await self.api_scheduler.submit(
                        coro_factory=lambda: self.sync_service.sync_thread(thread_id),
                        priority=10,
                    )
                    # 等待2秒，以极低的速率进行审计，避免触发API速率限制
                    await sleep(2)

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

    @audit_loop.before_loop
    async def before_audit_loop(self):
        """在循环开始前，等待机器人完全准备就绪。"""
        await self.bot.wait_until_ready()
        # logger.info("机器人已就绪，即将启动后台审计循环。")
