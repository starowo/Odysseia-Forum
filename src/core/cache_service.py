import logging
import discord
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select
from shared.models.thread import Thread

logger = logging.getLogger(__name__)

class CacheService:
    """
    一个统一的服务，用于缓存和提供整个机器人共享的数据状态。
    """
    def __init__(self, bot, session_factory: async_sessionmaker):
        self.bot = bot
        self.session_factory = session_factory
        self.indexed_channel_ids: set[int] = set()
        self.indexed_channels: dict[int, discord.ForumChannel] = {}
        logger.debug("CacheService 已初始化")

    async def build_or_refresh_cache(self):
        """
        从数据库加载数据，构建或刷新所有缓存。
        这个方法应该在机器人启动时和索引更新后被调用。
        """
        await self.bot.wait_until_ready()
        logger.debug("正在刷新 CacheService...")
        async with self.session_factory() as session:
            # 从数据库获取所有已索引的频道ID
            statement = select(Thread.channel_id).distinct()
            result = await session.execute(statement)
            self.indexed_channel_ids = set(result.scalars().all())

            new_channel_cache = {}
            for channel_id in self.indexed_channel_ids:
                channel = self.bot.get_channel(channel_id)
                if isinstance(channel, discord.ForumChannel):
                    new_channel_cache[channel_id] = channel
                else:
                    logger.warning(f"无法找到或频道类型错误 (ID: {channel_id})")
            self.indexed_channels = new_channel_cache

        logger.info(f"CacheService 刷新完毕。缓存了 {len(self.indexed_channel_ids)} 个频道ID 和 {len(self.indexed_channels)} 个频道对象。")

    def is_channel_indexed(self, channel_id: int) -> bool:
        """检查频道ID是否已索引。"""
        return channel_id in self.indexed_channel_ids

    def get_indexed_channels(self) -> list[discord.ForumChannel]:
        """获取所有已索引的频道对象列表。"""
        return list(self.indexed_channels.values())

    def get_indexed_channel_ids_set(self) -> set[int]:
        """从缓存中获取已索引的频道ID集合。"""
        return self.indexed_channel_ids

    def get_indexed_channel_ids_list(self) -> list[int]:
        """从缓存中获取已索引的频道ID列表。"""
        return list(self.indexed_channel_ids)
