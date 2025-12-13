import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord

from shared.safe_defer import safe_defer


class IndexerDashboard(discord.ui.View):
    """索引器仪表板视图，用于控制和显示索引过程。"""

    def __init__(self, cog, channel: discord.ForumChannel, config: dict):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel = channel
        self.interaction: Optional[discord.Interaction] = None
        self.config = config

        # 新增属性
        self.start_time: Optional[datetime] = None
        # 将令牌有效期设置为14.5分钟（870秒），留出一些缓冲时间
        self.token_expiry_duration = timedelta(seconds=870)

        # 从配置初始化消费者并发数和信号量
        self.consumer_concurrency = self.config.get("performance", {}).get(
            "indexer_concurrency", 5
        )
        self.consumer_semaphore = asyncio.Semaphore(self.consumer_concurrency)

        self.queue = asyncio.Queue()
        self.progress = {
            "discovered": 0,
            "processed": 0,
            "total": 0,
            "finished": False,
            "error": None,
            "failures": [],  # 用于记录非致命的处理失败
        }

        self._paused = asyncio.Event()
        self._paused.set()  # Initially not paused
        self._cancelled = asyncio.Event()
        self._update_lock = asyncio.Lock()
        self.ui_updater_task = None

    # 新增一个属性来判断令牌是否已过期
    @property
    def is_token_expired(self) -> bool:
        if not self.start_time:
            return True
        return datetime.now(timezone.utc) > self.start_time + self.token_expiry_duration

    async def start(self, interaction: discord.Interaction):
        """启动仪表板并发送初始消息。"""
        logging.debug(f"[{self.channel.id}] Dashboard.start() called.")
        self.interaction = interaction
        self.start_time = interaction.created_at  # 记录交互创建时间

        embed = self.create_embed()
        # build_index 中已经 defer，这里使用 edit_original_response 更新占位符
        await self.cog.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.edit_original_response(
                embed=embed, view=self
            ),
            priority=1,
        )
        self.cog.bot.loop.create_task(self.cog.run_indexer(self))
        self.ui_updater_task = self.cog.bot.loop.create_task(self.updater_loop())
        logging.debug(f"[{self.channel.id}] Dashboard.start() finished, tasks created.")

    def get_progress(self):
        """获取此特定索引作业的进度"""
        return self.progress

    def create_embed(self, progress_stats=None):
        """创建或更新嵌入消息"""
        progress_stats = progress_stats or self.get_progress()

        title = f"正在索引频道: {self.channel.name}"
        error = progress_stats.get("error")

        if error:
            state = "❌ 错误"
            color = discord.Color.red()
        elif self.is_paused():
            state = "⏸️ 已暂停"
            color = discord.Color.orange()
        elif self.is_cancelled():
            state = "⏹️ 已取消"
            color = discord.Color.greyple()
        elif progress_stats["finished"]:
            state = "✅ 已完成"
            color = discord.Color.green()
        else:
            state = "⚙️ 运行中"
            color = discord.Color.blue()

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="状态", value=state, inline=False)
        embed.add_field(
            name="已发现帖子", value=str(progress_stats["discovered"]), inline=True
        )
        embed.add_field(
            name="已处理帖子",
            value=f"{progress_stats['processed']} / {progress_stats.get('total', progress_stats['discovered'])}",
            inline=True,
        )

        if error:
            embed.add_field(name="致命错误", value=f"```\n{error}\n```", inline=False)

        failures = progress_stats.get("failures")
        if failures:
            # 为了避免 embed 过长，只显示前 5 个错误
            error_list = "\n".join(
                [f"- 帖子 {f['id']}: {f['reason']}" for f in failures[:5]]
            )
            if len(failures) > 5:
                error_list += f"\n...等 {len(failures) - 5} 个其他错误"

            embed.add_field(
                name=f"⚠️ 处理失败 ({len(failures)})",
                value=f"```\n{error_list}\n```",
                inline=False,
            )

        return embed

    async def updater_loop(self):
        """独立的UI更新循环"""
        logging.info(f"[{self.channel.id}] UI updater_loop started.")
        while not self.get_progress()["finished"] and not self.is_cancelled():
            # 在每次更新前检查令牌是否已过期
            if self.is_token_expired:
                logging.warning(
                    f"[{self.channel.id}] Interaction token is likely expired. "
                    "Stopping periodic UI updates to avoid errors."
                )
                break  # 退出循环，停止更新UI

            logging.debug(f"[{self.channel.id}] UI updater_loop tick.")
            await self.update_embed()
            await asyncio.sleep(2)  # 每2秒更新一次

        logging.info(
            f"[{self.channel.id}] UI updater_loop finished or was stopped. "
            "Waiting for final update signal from indexer."
        )
        # 循环结束后，不再调用 update_embed，等待 run_indexer 发出最终的更新指令

    async def update_embed(self):
        """更新嵌入消息"""
        if not self.interaction:
            return

        async with self._update_lock:
            embed = self.create_embed()
            progress = self.get_progress()

            if progress["finished"] or self.is_cancelled():
                self.pause_button.disabled = True
                self.cancel_button.disabled = True

            # 使用中等优先级更新进度，以免阻塞高优任务
            # logging.info(f"正在为频道 {self.channel.id} 更新UI...")
            await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: self.interaction.edit_original_response(
                    embed=embed, view=self
                ),
                priority=5,
            )

    @discord.ui.button(
        label="暂停", style=discord.ButtonStyle.secondary, custom_id="indexer_pause"
    )
    async def pause_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await safe_defer(interaction)
        if self._paused.is_set():
            self._paused.clear()
            button.label = "继续"
            button.style = discord.ButtonStyle.success
        else:
            self._paused.set()
            button.label = "暂停"
            button.style = discord.ButtonStyle.secondary

        await self.update_embed()

    @discord.ui.button(
        label="取消", style=discord.ButtonStyle.danger, custom_id="indexer_cancel"
    )
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await safe_defer(interaction)
        self._cancelled.set()
        if self.ui_updater_task:
            self.ui_updater_task.cancel()

        await self.update_embed()

    def is_paused(self) -> bool:
        return not self._paused.is_set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    async def wait_if_paused(self):
        await self._paused.wait()
