import discord
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ..cog import Search


class GlobalSearchView(discord.ui.View):
    """全局搜索命令的入口视图。"""

    def __init__(self, cog: "Search"):
        super().__init__(timeout=None)  # 持久化视图
        self.cog = cog

    @discord.ui.button(
        label="🌐 开始搜索",
        style=discord.ButtonStyle.success,
        custom_id="global_search_button",
        row=0,
    )
    async def start_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """处理按钮点击，启动全局搜索流程。"""
        await self.cog._start_global_search(interaction)

    @discord.ui.button(
        label="⚙️ 偏好设置",
        style=discord.ButtonStyle.secondary,
        custom_id="global_search_preferences_button",
        row=0,
    )
    async def preferences_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """分派一个事件来打开搜索偏好设置面板。"""
        # 分派一个自定义事件，由 PreferencesCog 监听
        self.cog.bot.dispatch("open_preferences_panel", interaction)

    @discord.ui.button(
        label="⭐ 查看收藏",
        style=discord.ButtonStyle.secondary,
        custom_id="global_search_collections_button",
        row=0,
    )
    async def collections_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """分派一个事件来启动收藏搜索流程。"""
        # 分派一个自定义事件，由 SearchCog 监听
        self.cog.bot.dispatch("open_collection_search", interaction)
