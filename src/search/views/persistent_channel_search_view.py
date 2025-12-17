from typing import TYPE_CHECKING

import discord

from search.strategies import DefaultSearchStrategy
from search.views import GenericSearchView
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from search.cog import Search


class PersistentChannelSearchView(discord.ui.View):
    """
    一个持久化的视图，包含一个按钮，用于在特定频道启动搜索。
    """

    def __init__(self, cog: "Search"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="🔍 搜索本频道",
        style=discord.ButtonStyle.primary,
        custom_id="persistent_channel_search_v2",
    )
    async def start_search(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """
        当用户点击“搜索本频道”按钮时，启动一个预设了频道ID的通用搜索流程。
        """

        await safe_defer(interaction, ephemeral=True)

        if not interaction.guild:
            await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 搜索交互信息不完整，无法继续。", ephemeral=True
                ),
                priority=1,
            )
            return

        if not isinstance(interaction.channel, discord.Thread):
            await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 此按钮必须在论坛的帖子内使用。", ephemeral=True
                ),
                priority=1,
            )
            return

        # 获取父频道 (channel) 和它的 ID (channel_id)
        channel = interaction.channel.parent
        if not channel:  # 预防帖子父频道丢失的罕见情况
            await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 无法找到该帖子的父频道\n如果重试后依然出现该提示，请联系技术员",
                    ephemeral=True,
                ),
                priority=1,
            )
            return

        channel_id = channel.id

        # 确保父频道是论坛
        if not isinstance(channel, discord.ForumChannel):
            await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 目标频道不是一个有效的论坛频道。", ephemeral=True
                ),
                priority=1,
            )
            return

        # 定义需要强制覆盖用户偏好的字段
        overrides = {
            "channel_ids": [channel_id],
            "page": 1,
        }

        # 使用 cog 中的辅助函数创建初始状态，确保所有偏好（包括时间）都被加载
        initial_state = await self.cog._create_initial_state_from_prefs(
            interaction.user.id, overrides
        )

        generic_view = GenericSearchView(
            cog=self.cog,
            interaction=interaction,
            search_state=initial_state,
            strategy=DefaultSearchStrategy(),
        )

        await generic_view.start(send_new_ephemeral=True)

    @discord.ui.button(
        label="⚙️ 偏好设置",
        style=discord.ButtonStyle.secondary,
        custom_id="persistent_channel_prefs_button",
        row=0,
    )
    async def preferences_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """
        分派一个事件来打开搜索偏好设置面板。
        """
        # 分派事件由 PreferencesCog 监听
        self.cog.bot.dispatch("open_preferences_panel", interaction)

    @discord.ui.button(
        label="⭐ 查看收藏",
        style=discord.ButtonStyle.secondary,
        custom_id="persistent_channel_collections_button",
        row=0,
    )
    async def collections_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """
        分派一个事件来启动收藏搜索流程。
        """
        # 分派事件由 SearchCog 监听
        self.cog.bot.dispatch("open_collection_search", interaction)
