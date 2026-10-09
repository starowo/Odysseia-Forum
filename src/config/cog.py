import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import async_sessionmaker

from config.general_config_handler import GeneralConfigHandler
from config.mutex_tags_handler import MutexTagsHandler
from shared.permissions import is_admin_or_bot_admin
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from bot_main import MyBot

# 获取一个模块级别的 logger
logger = logging.getLogger(__name__)


class Configuration(commands.Cog):
    """管理机器人各项配置"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.api_scheduler = bot.api_scheduler
        self.tag_service = bot.tag_cache_service
        self.mutex_handler = MutexTagsHandler(
            bot, self.session_factory, self.api_scheduler, self.tag_service
        )
        self.general_config_handler = GeneralConfigHandler(bot, self.session_factory)
        logger.info("Config 模块已加载")

    async def _ensure_main_guild(self, interaction: discord.Interaction) -> bool:
        """确保命令在主服务器使用，否则发送错误并返回 False。"""
        main_guild_id = self.bot._get_main_guild_id_from_config()
        if interaction.guild_id != main_guild_id:
            await interaction.response.send_message(
                f"❌ 此命令仅限在主服务器使用。\n"
                f"请前往主服务器：https://discord.com/channels/{main_guild_id}",
                ephemeral=True,
            )
            return False
        return True

    @commands.Cog.listener()
    async def on_config_updated(self):
        """
        监听全局的配置更新事件，并刷新缓存。
        """
        logger.debug("Configuration Cog 接收到 'config_updated' 事件，正在刷新缓存...")
        if self.bot.cache_service:
            await self.bot.cache_service.refresh_bot_config_cache()

    config_group = app_commands.Group(name="配置", description="管理机器人各项配置")

    @config_group.command(name="全局设置", description="打开BOT配置面板")
    @is_admin_or_bot_admin()
    async def general_settings(self, interaction: discord.Interaction):
        """唤出私密的BOT通用配置面板"""
        if not await self._ensure_main_guild(interaction):
            return
        await self.general_config_handler.start_flow(interaction)

    @config_group.command(name="互斥标签组", description="配置互斥标签组")
    @is_admin_or_bot_admin()
    async def configure_mutex_tags(self, interaction: discord.Interaction):
        """唤出私密的互斥标签组配置面板。"""
        if not await self._ensure_main_guild(interaction):
            return
        await self.mutex_handler.start_configuration_flow(interaction)

    @config_group.command(name="重载配置", description="重新加载配置文件")
    @is_admin_or_bot_admin()
    async def reload_config(self, interaction: discord.Interaction):
        """重新加载配置文件"""
        if not await self._ensure_main_guild(interaction):
            return
        await safe_defer(interaction, ephemeral=True)

        try:
            # 发送开始消息
            await interaction.followup.send("🔄 开始重载配置文件...", ephemeral=True)

            # 重载配置文件
            success, message = self.bot.reload_config()

            if not success:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                return

            # 发送配置重载成功消息
            await interaction.followup.send("✅ 配置文件重载成功！", ephemeral=True)

        except Exception as e:
            logger.error("重载配置时出错", exc_info=e)
            await interaction.followup.send(f"❌ 重载配置失败: {e}", ephemeral=True)

    @config_group.command(
        name="刷新缓存", description="手动刷新所有核心缓存（标签、频道、配置）"
    )
    @is_admin_or_bot_admin()
    async def refresh_cache(self, interaction: discord.Interaction):
        """手动刷新所有核心缓存"""
        if not await self._ensure_main_guild(interaction):
            return
        await safe_defer(interaction, ephemeral=True)

        try:
            await interaction.followup.send("🔄 开始刷新缓存...", ephemeral=True)

            if self.tag_service:
                await self.tag_service.build_cache()
            if self.bot.cache_service:
                await self.bot.cache_service.build_or_refresh_cache()

            await interaction.followup.send("🎉 所有缓存刷新完毕！", ephemeral=True)

        except Exception as e:
            logger.error("刷新缓存时出错", exc_info=e)
            await interaction.followup.send(f"❌ 刷新缓存失败: {e}", ephemeral=True)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """
        Cog 级别的应用程序命令错误处理器。
        """
        # 检查是否是权限检查失败
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ 你没有权限使用此命令。需要服务器管理员或被指定为机器人管理员。",
                ephemeral=True,
            )
        else:
            # 对于其他类型的错误，记录日志并发送通用错误消息
            command_name = interaction.command.name if interaction.command else "未知"
            logger.error(f"命令 '{command_name}' 发生错误", exc_info=error)
            # 检查交互是否已被响应
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ 命令执行时发生未知错误: {error}", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ 命令执行时发生未知错误: {error}", ephemeral=True
                )
