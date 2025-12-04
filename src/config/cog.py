import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, cast
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.safe_defer import safe_defer

from .mutex_tags_handler import MutexTagsHandler
from .general_config_handler import GeneralConfigHandler
from core.tag_service import TagService
from .config_service import ConfigService

if TYPE_CHECKING:
    from bot_main import MyBot

# 获取一个模块级别的 logger
logger = logging.getLogger(__name__)


# 自定义权限检查函数
def is_admin_or_bot_admin():
    """
    一个自定义的检查函数，用于验证用户是否为服务器管理员或在 config.json 中定义的机器人管理员。
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        # 为了让类型检查器知道 interaction.client 是我们自定义的 MyBot 类型，这里进行类型转换
        bot = cast("MyBot", interaction.client)

        # 确保 bot 实例和 config 属性存在
        if not hasattr(bot, "config"):
            return False

        # 检查用户是否为在配置文件中指定的机器人管理员
        bot_admin_ids = bot.config.get("bot_admin_user_ids", [])
        if interaction.user.id in bot_admin_ids:
            return True

        # 检查用户是否为服务器管理员
        # 在服务器（guild）上下文中，interaction.user 是 discord.Member 类型，拥有 guild_permissions 属性
        if (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.administrator
        ):
            return True

        return False

    return app_commands.check(predicate)


class Configuration(commands.Cog):
    """管理机器人各项配置"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        api_scheduler,
        tag_service: TagService,
        config_service: ConfigService,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.api_scheduler = api_scheduler
        self.tag_service = tag_service
        self.config_service = config_service
        self.mutex_handler = MutexTagsHandler(
            bot, self.session_factory, self.api_scheduler, self.tag_service
        )
        self.general_config_handler = GeneralConfigHandler(
            bot, self.session_factory, self.config_service
        )
        logger.info("Config 模块已加载")

    @commands.Cog.listener()
    async def on_config_updated(self):
        """
        监听全局的配置更新事件，并刷新缓存。
        """
        logger.debug("Configuration Cog 接收到 'config_updated' 事件，正在刷新缓存...")
        if self.config_service:
            await self.config_service.build_or_refresh_cache()

    config_group = app_commands.Group(name="配置", description="管理机器人各项配置")

    @config_group.command(name="全局设置", description="打开BOT配置面板")
    @is_admin_or_bot_admin()
    async def general_settings(self, interaction: discord.Interaction):
        """唤出私密的BOT通用配置面板"""
        await self.general_config_handler.start_flow(interaction)

    @general_settings.error
    async def on_general_settings_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ 你没有权限使用此命令。需要服务器管理员或被指定为机器人管理员。",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"❌ 命令执行失败: {error}", ephemeral=True
            )

    @config_group.command(name="互斥标签组", description="配置互斥标签组")
    @app_commands.checks.has_permissions(administrator=True)
    async def configure_mutex_tags(self, interaction: discord.Interaction):
        """唤出私密的互斥标签组配置面板。"""
        await self.mutex_handler.start_configuration_flow(interaction)

    @configure_mutex_tags.error
    async def on_mutex_tags_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ 此命令需要 admin 权限", ephemeral=True
            )
        else:
            logger.error("配置互斥标签命令出错", exc_info=error)
            await interaction.response.send_message(
                f"❌ 命令执行失败: {error}", ephemeral=True
            )

    @config_group.command(
        name="重载配置", description="重新加载配置文件并重新导出部署网页"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_config(self, interaction: discord.Interaction):
        """重新加载配置文件并重新导出部署网页"""
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
            await interaction.followup.send(
                "✅ 配置文件重载成功！开始重新部署网页...", ephemeral=True
            )

            # 执行手动同步和部署
            await manual_sync(self.bot, self.bot.config)

            # 发送完成消息
            await interaction.followup.send(
                "✅ 配置重载并重新部署完成！", ephemeral=True
            )

        except Exception as e:
            logger.error("重载配置时出错", exc_info=e)
            await interaction.followup.send(f"❌ 重载配置失败: {e}", ephemeral=True)

    @reload_config.error
    async def on_reload_config_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ 此命令需要 admin 权限。", ephemeral=True
            )
        else:
            logger.error("重载配置命令出错", exc_info=error)
            await interaction.response.send_message(
                f"❌ 命令执行失败: {error}", ephemeral=True
            )

    @config_group.command(name="缓存状态", description="查看用户昵称缓存状态")
    @app_commands.checks.has_permissions(administrator=True)
    async def view_cache_status(self, interaction: discord.Interaction):
        """查看用户昵称缓存状态"""
        await safe_defer(interaction, ephemeral=True)

        try:
            # 获取同步服务实例
            sync_service = get_sync_service(self.bot, self.bot.config)
            cache_stats = sync_service.get_cache_stats()

            # 构建状态消息
            status_message = "📊 **用户昵称缓存状态**\n\n"
            status_message += f"**缓存条目数**: {cache_stats['total_cached_users']}\n"

            if cache_stats["sample_entries"]:
                status_message += "\n**示例条目** (显示前5个):\n"
                for (guild_id, user_id), nickname in cache_stats[
                    "sample_entries"
                ].items():
                    status_message += (
                        f"• 服务器 {guild_id} - 用户 {user_id}: `{nickname}`\n"
                    )
            else:
                status_message += "\n**缓存为空**"

            await interaction.followup.send(status_message, ephemeral=True)

        except Exception as e:
            logger.error("查看缓存状态时出错", exc_info=e)
            await interaction.followup.send(f"❌ 获取缓存状态失败: {e}", ephemeral=True)

    @config_group.command(name="清除缓存", description="清除所有用户昵称缓存")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_cache(self, interaction: discord.Interaction):
        """清除所有用户昵称缓存"""
        await safe_defer(interaction, ephemeral=True)

        try:
            # 获取同步服务实例
            sync_service = get_sync_service(self.bot, self.bot.config)
            cache_stats_before = sync_service.get_cache_stats()

            # 清除缓存
            sync_service.clear_all_cache()

            await interaction.followup.send(
                f"✅ 已清除用户昵称缓存！\n"
                f"**清除前条目数**: {cache_stats_before['total_cached_users']}\n"
                f"**清除后条目数**: 0",
                ephemeral=True,
            )

        except Exception as e:
            logger.error("清除缓存时出错", exc_info=e)
            await interaction.followup.send(f"❌ 清除缓存失败: {e}", ephemeral=True)

    @view_cache_status.error
    async def on_view_cache_status_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ 此命令需要 admin 权限。", ephemeral=True
            )
        else:
            logger.error("查看缓存状态命令出错", exc_info=error)
            await interaction.response.send_message(
                f"❌ 命令执行失败: {error}", ephemeral=True
            )

    @clear_cache.error
    async def on_clear_cache_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ 此命令需要 admin 权限。", ephemeral=True
            )
        else:
            logger.error("清除缓存命令出错", exc_info=error)
            await interaction.response.send_message(
                f"❌ 命令执行失败: {error}", ephemeral=True
            )
