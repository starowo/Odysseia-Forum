import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import async_sessionmaker
from shared.safe_defer import safe_defer
from ThreadManager.cog import ThreadManager
from core.tag_service import TagService
from core.sync_service import SyncService
from .views import IndexerDashboard


if TYPE_CHECKING:
    from bot_main import MyBot

# 获取一个模块级别的 logger
logger = logging.getLogger(__name__)


class Indexer(commands.Cog):
    """构建索引相关命令"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
        tag_service: TagService,
        sync_service: SyncService,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.tag_service = tag_service
        self.sync_service = sync_service
        logger.info("Indexer 模块已加载")

    @app_commands.command(
        name="构建索引", description="对当前论坛频道的所有帖子进行索引"
    )
    async def build_index(self, interaction: discord.Interaction):
        await safe_defer(interaction, ephemeral=True)
        if not isinstance(interaction.channel, discord.Thread):
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "请在论坛频道的帖子内使用此命令", ephemeral=True
                ),
                priority=1,
            )
            return

        channel = interaction.channel.parent
        if not isinstance(channel, discord.ForumChannel):
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "此命令仅适用于论坛频道。", ephemeral=True
                ),
                priority=1,
            )
            return

        dashboard = IndexerDashboard(self, channel, self.config)
        await dashboard.start(interaction)

    async def run_indexer(self, dashboard: IndexerDashboard):
        """运行生产者和消费者任务"""
        logging.debug(f"[{dashboard.channel.id}] run_indexer 开始")

        # 步骤 1: 预同步该频道的所有可用标签，避免后续的并发冲突
        try:
            thread_manager_cog = cast(ThreadManager, self.bot.get_cog("ThreadManager"))
            if thread_manager_cog:
                await thread_manager_cog.pre_sync_forum_tags(dashboard.channel)
            else:
                logging.warning(
                    f"[{dashboard.channel.id}] 无法获取 ThreadManager Cog，跳过标签预同步。"
                )
        except Exception as e:
            # 如果预同步失败，记录一个致命错误并停止索引
            logging.error(
                f"[{dashboard.channel.id}] 预同步标签时发生严重错误，索引已中止: {e}",
                exc_info=True,
            )
            dashboard.progress["error"] = f"预同步标签失败: {e}"
            dashboard.progress["finished"] = True
            await dashboard.update_embed()
            return

        # 步骤 2: 启动生产者和消费者
        logging.info(
            f"[{dashboard.channel.id}] 标签预同步完成，启动 {dashboard.consumer_concurrency} 个消费者"
        )
        loop = self.bot.loop
        producer_task = loop.create_task(self.producer(dashboard))
        consumer_tasks = [
            loop.create_task(self.consumer(dashboard, consumer_id=i))
            for i in range(dashboard.consumer_concurrency)
        ]

        try:
            # 等待生产者完成（所有帖子都被发现并放入队列）
            await producer_task

            # 等待队列中的所有项目都被消费者处理
            await dashboard.queue.join()

        except Exception as e:
            dashboard.progress["error"] = f"{type(e).__name__}: {e}"
            producer_task.cancel()  # 如果出错，也取消生产者
            dashboard.progress["finished"] = True
        finally:
            # 所有项目处理完毕，取消所有消费者任务
            for task in consumer_tasks:
                task.cancel()

            # 等待所有被取消的消费者任务完全停止
            await asyncio.gather(*consumer_tasks, return_exceptions=True)

            # 标记完成并更新UI
            if not dashboard.progress.get("error"):
                dashboard.progress["finished"] = True

            # 检查令牌是否已过期来决定如何发送最终状态
            if dashboard.is_token_expired:
                # 令牌已过期，发送一条新消息
                # logging.info(f"[{dashboard.channel.id}] Token expired. Sending a new message for final status.")
                final_embed = dashboard.create_embed()
                if not dashboard.interaction:
                    logging.error(
                        f"[{dashboard.channel.id}] Dashboard interaction is None, cannot send final message."
                    )
                    return

                interaction = dashboard.interaction
                user_mention = interaction.user.mention
                await dashboard.cog.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        content=f"{user_mention}，索引任务已完成。",
                        embed=final_embed,
                        ephemeral=True,
                    ),
                    priority=2,  # 中等优先级
                )
            else:
                # 令牌仍然有效，安全地编辑原始消息
                # logging.info(f"[{dashboard.channel.id}] Token is still valid. Performing final UI update.")
                await dashboard.update_embed()

            # 分发全局事件
            if not dashboard.progress.get("error"):
                logging.info(
                    f"[{dashboard.channel.id}] 索引完成，分发 'index_updated' 事件。"
                )
                self.bot.dispatch("index_updated")

    async def producer(self, dashboard: IndexerDashboard):
        """生产者：发现帖子并放入队列"""
        channel = dashboard.channel
        progress = dashboard.progress
        queue = dashboard.queue

        # 活跃线程 (来自缓存，无API调用)
        for thread in channel.threads:
            await queue.put(thread)
            progress["discovered"] += 1

        # 已归档线程 (手动分页)
        before_timestamp = None
        while not dashboard.is_cancelled():
            batch = []
            try:
                async for thread in channel.archived_threads(
                    limit=100, before=before_timestamp
                ):
                    batch.append(thread)
                    await queue.put(thread)
                    progress["discovered"] += 1
            except Exception as e:
                logging.error(f"[{channel.id}] 获取归档帖子时出错: {e}", exc_info=True)
                pass

            if not batch:
                break

            before_timestamp = batch[-1].archive_timestamp

        if not dashboard.is_cancelled():
            progress["total"] = progress["discovered"]

        # 生产者完成

    async def consumer(self, dashboard: IndexerDashboard, consumer_id: int):
        """消费者：从队列中取出帖子并处理，受信号量控制。"""
        try:
            while True:
                await dashboard.wait_if_paused()
                if dashboard.is_cancelled():
                    break

                async with dashboard.consumer_semaphore:
                    if (
                        dashboard.is_cancelled()
                    ):  # 再次检查，因为可能在等待信号量时被取消
                        break

                    thread = await dashboard.queue.get()

                    try:
                        await self.sync_service.sync_thread(
                            thread, fetch_if_incomplete=True
                        )
                    except Exception as e:
                        error_reason = f"{type(e).__name__}"
                        logging.error(
                            f"消费者 #{consumer_id} 处理帖子 {thread.id} 时出错: {e}",
                            exc_info=True,
                        )
                        dashboard.progress["failures"].append(
                            {"id": thread.id, "reason": error_reason}
                        )
                    finally:
                        # 无论成功还是失败，都将帖子标记为“已处理”，以确保进度条最终能达到100%
                        dashboard.progress["processed"] += 1
                        dashboard.queue.task_done()

        except asyncio.CancelledError:
            # logging.info(f"消费者 #{consumer_id} 被取消")
            pass

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        """
        监听频道更新事件。
        只要论坛频道的标签发生任何变化（增、删、改），就重建 TagService 的缓存。
        """
        if not isinstance(after, discord.ForumChannel) or not isinstance(
            before, discord.ForumChannel
        ):
            return

        # 如果可用标签列表没有发生任何变化，则提前返回，避免不必要的操作。
        if before.available_tags == after.available_tags:
            return

        logging.info(
            f"检测到论坛频道 '{after.name}' (ID: {after.id}) 的标签发生变化，准备刷新 TagService 缓存。"
        )

        try:
            # 调用服务重建整个缓存，确保数据完全同步
            await self.tag_service.build_cache()
            logging.info("TagService 缓存已因频道更新而成功刷新。")
        except Exception as e:
            logging.error(
                f"因频道更新事件刷新 TagService 缓存时出错: {e}", exc_info=True
            )
