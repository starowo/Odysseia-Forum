import discord
from typing import TYPE_CHECKING

from shared.safe_defer import safe_defer
from .generic_search_view import GenericSearchView
from ..dto.search_state import SearchStateDTO

if TYPE_CHECKING:
    from ..cog import Search


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
        if not channel: # 预防帖子父频道丢失的罕见情况
             await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 无法找到该帖子的父频道。", ephemeral=True
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

        # 获取用户偏好
        user_prefs = await self.cog.preferences_service.get_user_preferences(
            interaction.user.id
        )
        
        # 获取该频道的标签
        channel_tags = self.cog.get_merged_tags([channel_id])
        channel_tag_names = [tag.name for tag in channel_tags]

        # 创建初始状态
        if user_prefs:
            initial_state = SearchStateDTO(
                channel_ids=[channel_id],
                include_authors=set(user_prefs.include_authors or []),
                exclude_authors=set(user_prefs.exclude_authors or []),
                include_tags=set(user_prefs.include_tags or []),
                exclude_tags=set(user_prefs.exclude_tags or []),
                all_available_tags=channel_tag_names,
                keywords=user_prefs.include_keywords or "",
                exclude_keywords=user_prefs.exclude_keywords or "",
                exemption_markers=user_prefs.exclude_keyword_exemption_markers,
                page=1,
                results_per_page=user_prefs.results_per_page,
                preview_image_mode=user_prefs.preview_image_mode,
            )
        else:
            initial_state = SearchStateDTO(
                channel_ids=[channel_id], all_available_tags=channel_tag_names, page=1
            )

        generic_view = GenericSearchView(
            cog=self.cog,
            interaction=interaction,
            search_state=initial_state,
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