import logging
from typing import TYPE_CHECKING, Optional

import discord

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class DiscordUtils:
    """
    操控 Discord API 的工具类。
    所有方法都是静态的，不维护任何状态。
    """

    @staticmethod
    async def get_or_fetch_user(
        bot: "MyBot",
        user_id: int,
        guild: Optional[discord.Guild] = None,
        source_member: Optional[discord.Member | discord.User] = None,
    ) -> Optional[discord.User | discord.Member]:
        """
        获取或抓取 Discord 用户/成员对象。
        策略：传入对象 -> 服务器缓存 -> 机器人全局缓存 -> API 调用。

        Args:
            bot: MyBot 实例
            user_id: 目标用户的 Discord ID
            guild: 可选的服务器对象，用于从服务器缓存中查找成员
            source_member: 可选的直接传入的用户/成员对象

        Returns:
            如果成功找到用户，返回 discord.User 或 discord.Member 对象；否则返回 None。
        """
        user_obj: Optional[discord.User | discord.Member] = None

        # 优先使用直接传入的 source_member/user 对象
        if source_member and source_member.id == user_id:
            user_obj = source_member

        # 尝试从服务器成员缓存中获取
        if not user_obj and guild:
            user_obj = guild.get_member(user_id)

        # 尝试从机器人全局用户缓存中获取
        if not user_obj:
            user_obj = bot.get_user(user_id)

        # 最后手段：API 调用
        if not user_obj:
            try:
                # 使用调度器来避免速率限制
                user_obj = await bot.api_scheduler.submit(
                    coro_factory=lambda: bot.fetch_user(user_id),
                    priority=8,  # 优先级略低于帖子同步
                )
            except discord.NotFound:
                logger.warning(f"无法通过 API 找到 ID 为 {user_id} 的用户。")
                return None
            except Exception as e:
                logger.error(
                    f"通过API获取用户 {user_id} 信息时出错: {e}", exc_info=True
                )
                return None

        if not user_obj:
            logger.warning(f"所有方法都无法获取 ID 为 {user_id} 的用户对象。")
            return None

        return user_obj

