"""共享的权限检查装饰器。"""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


async def check_is_admin_or_bot_admin(interaction: discord.Interaction) -> bool:
    """
    检查用户是否为服务器管理员或在 config.json 中定义的机器人管理员。

    可用于 View 按钮回调等非斜杠命令场景。
    """
    bot = cast("MyBot", interaction.client)

    if not hasattr(bot, "config"):
        return False

    bot_admin_ids = bot.config.get("bot_admin_user_ids", [])
    if interaction.user.id in bot_admin_ids:
        return True

    if (
        isinstance(interaction.user, discord.Member)
        and interaction.user.guild_permissions.administrator
    ):
        return True

    return False


async def check_can_review_banner(interaction: discord.Interaction) -> bool:
    """检查用户是否拥有 Banner 审核权限。"""
    if await check_is_admin_or_bot_admin(interaction):
        return True

    bot = cast("MyBot", interaction.client)
    management_role_id = bot.config.get("management_role_id")
    if not management_role_id or not isinstance(interaction.user, discord.Member):
        return False

    try:
        expected_role_id = int(management_role_id)
    except (TypeError, ValueError):
        logger.warning("management_role_id 无法解析，管理组 Banner 审核权限未启用")
        return False

    return any(role.id == expected_role_id for role in interaction.user.roles)


def is_admin_or_bot_admin():
    """
    自定义 app_commands.check 装饰器，验证用户是否为服务器管理员或在 config.json 中定义的机器人管理员。

    用于斜杠命令的权限控制。
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        return await check_is_admin_or_bot_admin(interaction)

    return app_commands.check(predicate)
