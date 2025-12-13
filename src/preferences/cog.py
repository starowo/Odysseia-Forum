import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import async_sessionmaker

from preferences.preferences_service import PreferencesService
from preferences.views.preferences_view import PreferencesView
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class Preferences(commands.Cog):
    """用户偏好设置相关命令"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
        preferences_service: PreferencesService,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.preferences_service = preferences_service
        logger.info("Preferences 模块已加载")

    async def cog_load(self):
        """在Cog加载时注册上下文菜单命令"""

        # --- 手动创建和注册上下文菜单 ---
        add_block_menu = app_commands.ContextMenu(
            name="加入搜索屏蔽", callback=self.add_to_search_blocklist
        )
        remove_block_menu = app_commands.ContextMenu(
            name="移出搜索屏蔽", callback=self.remove_from_search_blocklist
        )
        self.bot.tree.add_command(add_block_menu)
        self.bot.tree.add_command(remove_block_menu)

    search_prefs = app_commands.Group(name="搜索偏好", description="管理搜索偏好设置")

    @search_prefs.command(name="作者", description="管理作者偏好设置")
    @app_commands.describe(action="操作类型", user="要设置的用户（@用户 或 用户ID）")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="只看作者", value="include"),
            app_commands.Choice(name="屏蔽作者", value="exclude"),
            app_commands.Choice(name="取消屏蔽", value="unblock"),
            app_commands.Choice(name="清空作者偏好", value="clear"),
        ]
    )
    async def search_preferences_author(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        user: Optional[discord.User] = None,
    ):
        """管理作者偏好设置"""
        # 这里的逻辑已经大部分在 PreferencesService 中，所以直接调用
        await self.preferences_service.search_preferences_author(
            interaction, action, user
        )

    @search_prefs.command(name="设置", description="打开偏好设置面板")
    async def open_search_preferences_panel(self, interaction: discord.Interaction):
        """打开一个新的交互式视图来管理搜索偏好"""
        await self._open_search_preferences_panel(interaction)

    async def _open_search_preferences_panel(self, interaction: discord.Interaction):
        """打开偏好设置面板"""
        try:
            await safe_defer(interaction, ephemeral=True)

            view = PreferencesView(self.preferences_service, interaction)
            await view.start()
        except Exception as e:
            logger.error(f"打开偏好设置面板时出错: {e}", exc_info=True)
            if not interaction.response.is_done():
                await safe_defer(interaction, ephemeral=True)
            await interaction.followup.send(
                f"❌ 打开设置面板时发生错误: {e}", ephemeral=True
            )

    # 上下文菜单命令的回调函数
    async def add_to_search_blocklist(
        self, interaction: discord.Interaction, user: discord.User
    ):
        """将用户加入搜索屏蔽列表"""
        action = app_commands.Choice(name="屏蔽作者", value="exclude")
        await self.preferences_service.search_preferences_author(
            interaction, action, user
        )

    async def remove_from_search_blocklist(
        self, interaction: discord.Interaction, user: discord.User
    ):
        """将用户从搜索屏蔽列表中移除"""
        action = app_commands.Choice(name="取消屏蔽", value="unblock")
        await self.preferences_service.search_preferences_author(
            interaction, action, user
        )

    @commands.Cog.listener("on_open_preferences_panel")
    async def on_open_preferences_panel_listener(
        self, interaction: discord.Interaction
    ):
        """监听从其他视图（如GlobalSearchView）发出的事件，以打开偏好面板。"""
        # 调用内部逻辑函数
        await self._open_search_preferences_panel(interaction)
