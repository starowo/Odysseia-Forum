import logging
from collections import defaultdict

import discord
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.thread_service import ThreadService

logger = logging.getLogger(__name__)


class CacheService:
    """
    缓存 BOT 共享数据的服务<br>
    目前存储的数据包括：已索引的频道（按 guild 分组）
    """

    def __init__(self, bot, session_factory: async_sessionmaker):
        self.bot = bot
        self.session_factory = session_factory
        self.indexed_channel_ids: set[int] = set()
        self.indexed_channels: dict[int, discord.ForumChannel] = {}
        # guild_id -> {channel_id -> ForumChannel}
        self.guild_channels: dict[int, dict[int, discord.ForumChannel]] = {}
        logger.debug("CacheService 已初始化")

    async def build_or_refresh_cache(self):
        """
        从数据库加载数据，构建或刷新所有缓存。
        这个方法应该在机器人启动时和索引更新后被调用。
        """
        logger.debug("正在刷新 CacheService...")
        async with self.session_factory() as session:
            thread_service = ThreadService(session)
            indexed_channel_ids = await thread_service.get_all_indexed_channel_ids()
            self.indexed_channel_ids = set(indexed_channel_ids)

        new_channel_cache: dict[int, discord.ForumChannel] = {}
        new_guild_channels: dict[int, dict[int, discord.ForumChannel]] = defaultdict(dict)

        for channel_id in self.indexed_channel_ids:
            channel = await self._get_channel_safely(channel_id)
            if channel and isinstance(channel, discord.ForumChannel):
                new_channel_cache[channel_id] = channel
                new_guild_channels[channel.guild.id][channel_id] = channel
            elif channel:
                logger.warning(f"频道 (ID: {channel_id}) 不是论坛频道，已跳过。")

        self.indexed_channels = new_channel_cache
        self.guild_channels = dict(new_guild_channels)

        logger.info(
            f"CacheService 刷新完毕。缓存了 {len(self.indexed_channel_ids)} 个频道ID，"
            f"{len(self.indexed_channels)} 个频道对象，涉及 {len(self.guild_channels)} 个服务器。"
        )

    async def _get_channel_safely(
        self, channel_id: int
    ) -> discord.ForumChannel | None:
        """优先从缓存获取频道，失败则从 API 获取。"""
        channel = self.bot.get_channel(channel_id)
        if channel:
            return channel

        try:
            return await self.bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.warning(f"无法找到频道 (ID: {channel_id})，机器人可能不在该服务器中。")
        except discord.Forbidden:
            logger.warning(f"没有权限访问频道 (ID: {channel_id})。")
        except Exception as e:
            logger.error(f"获取频道 (ID: {channel_id}) 时发生未知错误: {e}")
        return None

    def is_channel_indexed(self, channel_id: int) -> bool:
        """检查频道ID是否已索引。"""
        return channel_id in self.indexed_channel_ids

    def get_indexed_channels(self, guild_id: int | None = None) -> list[discord.ForumChannel]:
        """获取已索引的频道对象列表。可选按 guild_id 过滤。"""
        if guild_id is not None:
            guild_data = self.guild_channels.get(guild_id, {})
            return list(guild_data.values())
        return list(self.indexed_channels.values())

    def get_indexed_channel_ids_set(self, guild_id: int | None = None) -> set[int]:
        """从缓存中获取已索引的频道ID集合。可选按 guild_id 过滤。"""
        if guild_id is not None:
            return set(self.guild_channels.get(guild_id, {}).keys())
        return self.indexed_channel_ids

    def get_indexed_channel_ids_list(self, guild_id: int | None = None) -> list[int]:
        """从缓存中获取已索引的频道ID列表。可选按 guild_id 过滤。"""
        return list(self.get_indexed_channel_ids_set(guild_id))
