import asyncio
import json
import logging
from collections import defaultdict

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select as sm_select

from core.booklist_item_repository import BooklistItemRepository
from core.null_bot import NullBot
from core.thread_repository import ThreadRepository
from dto.bot_config_dto import BotConfigDTO
from dto.meta.category_meta import CategoryMeta
from dto.meta.channel_meta import ChannelMeta
from dto.meta.guild_meta import GuildMeta
from dto.meta.tag_meta import TagMeta
from dto.search import SearchConfigDTO
from models import BotConfig
from shared.enum import CacheKeys, SearchConfigDefaults, SearchConfigType

logger = logging.getLogger(__name__)


class ApiCacheService:
    """
    API 进程专用的缓存服务，不依赖 discord.Client。

    从 Redis 加载频道元数据（由 Bot 进程发布），从数据库加载 BotConfig。
    启动定时轮询任务，自动同步频道元数据和配置变更。
    """

    def __init__(self, session_factory: async_sessionmaker, redis_client):
        self.bot = NullBot()
        self.session_factory = session_factory
        self._redis = redis_client
        self.indexed_channel_ids: set[int] = set()
        # int -> ChannelMeta
        self.indexed_channels: dict[int, ChannelMeta] = {}
        # guild_id -> {channel_id -> ChannelMeta}
        self.guild_channels: dict[int, dict[int, ChannelMeta]] = {}
        self.bot_configs: dict[SearchConfigType, BotConfigDTO] = {}
        self._task: asyncio.Task | None = None
        self._is_running = False
        logger.debug("ApiCacheService 已初始化")

    # ── 公开接口（与 CacheService 完全一致）─────────────────────

    async def build_cache(self):
        """首次构建缓存。"""
        await self._refresh_indexed_channel_ids()
        await self._load_channel_metadata_from_redis(retry_on_missing=True)
        await self.refresh_bot_config_cache()
        logger.info(
            f"ApiCacheService 缓存构建完毕。"
            f"已索引 {len(self.indexed_channel_ids)} 个频道，"
            f"加载了 {len(self.indexed_channels)} 个频道元数据，"
            f"缓存了 {len(self.bot_configs)} 个 BotConfig 配置项。"
        )

    def start(self):
        """启动定时同步后台任务。"""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._periodic_sync())
        logger.info("ApiCacheService 定时同步已启动（每 60 秒一次）")

    async def stop(self):
        """停止定时同步任务。"""
        if not self._is_running:
            return
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ApiCacheService 定时同步已停止")

    async def get_bot_config(
        self, config_type: SearchConfigType
    ) -> BotConfigDTO | None:
        """从缓存获取配置；如未命中则自动刷新后重试。"""
        config = self.bot_configs.get(config_type)
        if config is not None:
            return config

        logger.info(f"ApiCacheService 配置缓存未命中: {config_type.name}，正在刷新...")
        await self.refresh_bot_config_cache()
        config = self.bot_configs.get(config_type)
        if config is None:
            logger.error(f"刷新缓存后仍然找不到配置: {config_type.name}.")
        return config

    async def get_ucb1_config(self) -> SearchConfigDTO:
        """获取搜索算法所需的配置参数。"""
        total_disp_conf = await self.get_bot_config(
            SearchConfigType.TOTAL_DISPLAY_COUNT
        )
        ucb_factor_conf = await self.get_bot_config(
            SearchConfigType.UCB1_EXPLORATION_FACTOR
        )
        strength_conf = await self.get_bot_config(SearchConfigType.STRENGTH_WEIGHT)
        reddit_hot_conf = await self.get_bot_config(
            SearchConfigType.REDDIT_HOT_TIME_DECAY
        )

        total_display_count = (
            total_disp_conf.value_int
            if total_disp_conf and total_disp_conf.value_int is not None
            else 1
        )
        exploration_factor = (
            ucb_factor_conf.value_float
            if ucb_factor_conf and ucb_factor_conf.value_float is not None
            else SearchConfigDefaults.UCB1_EXPLORATION_FACTOR.value
        )
        strength_weight = (
            strength_conf.value_float
            if strength_conf and strength_conf.value_float is not None
            else SearchConfigDefaults.STRENGTH_WEIGHT.value
        )
        reddit_hot_time_decay = (
            reddit_hot_conf.value_float
            if reddit_hot_conf and reddit_hot_conf.value_float is not None
            else SearchConfigDefaults.REDDIT_HOT_TIME_DECAY.value
        )

        return SearchConfigDTO(
            total_display_count=total_display_count,
            exploration_factor=exploration_factor,
            strength_weight=strength_weight,
            reddit_hot_time_decay=reddit_hot_time_decay,
        )

    async def refresh_bot_config_cache(self):
        """从数据库刷新 BotConfig 缓存。"""
        async with self.session_factory() as session:
            result = await session.execute(sm_select(BotConfig))
            all_configs = result.scalars().all()

        self.bot_configs = {
            SearchConfigType(config.type): BotConfigDTO.from_orm(config)
            for config in all_configs
            if config.type in SearchConfigType._value2member_map_
        }

    def is_channel_indexed(self, channel_id: int) -> bool:
        """检查频道ID是否已索引。"""
        return channel_id in self.indexed_channel_ids

    def get_indexed_channels(self, guild_id: int | None = None) -> list[ChannelMeta]:
        """获取已索引的频道元数据列表。可选按 guild_id 过滤。"""
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

    async def get_tournament_info_batch(
        self, session, thread_ids: list[int]
    ) -> dict[int, list[dict]]:
        """
        批量获取 thread_id → [TournamentInfo] 映射。

        优先 Redis MGET，未命中则 DB 补查并回填。
        Redis Key: ``tournament:thread:{thread_id}``, TTL 1h。
        空结果也缓存（"[]"），避免反复穿透。
        """
        if not thread_ids:
            return {}

        keys = [CacheKeys.TOURNAMENT_THREAD.format(thread_id=tid) for tid in thread_ids]
        result: dict[int, list[dict]] = {}
        miss_ids: list[int] = []

        # ── MGET 批量读 ──
        try:
            cached = await self._redis.mget(keys)
            for tid, val in zip(thread_ids, cached):
                if val:
                    result[tid] = json.loads(val)
                else:
                    miss_ids.append(tid)
        except Exception:
            logger.warning("Redis MGET 赛事缓存失败，降级全走 DB", exc_info=True)
            miss_ids = thread_ids

        # ── DB 补查未命中 ──
        if miss_ids:
            repo = BooklistItemRepository(session)
            db_map = await repo.get_tournament_info_by_thread_ids(miss_ids)

            # ── 回填 Redis ──
            for tid in miss_ids:
                infos = db_map.get(tid, [])
                key = CacheKeys.TOURNAMENT_THREAD.format(thread_id=tid)
                try:
                    if infos:
                        await self._redis.setex(key, 3600, json.dumps(infos))
                    else:
                        await self._redis.setex(key, 3600, "[]")
                except Exception:
                    pass

            result.update(db_map)

        return result

    # ── 内部方法 ─────────────────────────────────────────────

    async def _refresh_indexed_channel_ids(self):
        """从数据库加载已索引频道 ID 集合。"""
        async with self.session_factory() as session:
            thread_service = ThreadRepository(session)
            indexed_channel_ids = await thread_service.get_all_indexed_channel_ids()
            self.indexed_channel_ids = set(indexed_channel_ids)

    async def _load_channel_metadata_from_redis(self, retry_on_missing: bool = False):
        """从 Redis 加载由 Bot 进程发布的频道元数据。"""
        try:
            raw = await self._redis.get("cache:forum-channels")

            # ── 启动重试：Bot 进程可能尚未发布元数据 ──
            if not raw and retry_on_missing:
                logger.info("等待 Bot 发布频道元数据到 Redis...")
                for attempt in range(1, 31):
                    await asyncio.sleep(1)
                    try:
                        raw = await self._redis.get("cache:forum-channels")
                    except Exception:
                        logger.debug(f"Redis 读取失败（第 {attempt} 次），将继续重试")
                        continue
                    if raw:
                        logger.info(f"频道元数据已就绪（等待了 {attempt} 秒）")
                        break
                else:
                    logger.warning("等待超时：Bot 未在 30 秒内发布频道元数据")
                    return

            if not raw:
                logger.warning("Redis 中无频道元数据（Bot 可能尚未发布）")
                return

            channels_list = json.loads(raw)
            new_channels: dict[int, ChannelMeta] = {}
            new_guild_channels: dict[int, dict[int, ChannelMeta]] = defaultdict(dict)

            for entry in channels_list:
                channel_id = entry["id"]
                guild_data = entry["guild"]
                guild = GuildMeta(id=guild_data["id"], name=guild_data["name"])

                category = None
                if entry.get("category"):
                    cat_data = entry["category"]
                    category = CategoryMeta(id=cat_data["id"], name=cat_data["name"])

                tags = [
                    TagMeta(id=t["id"], name=t["name"])
                    for t in entry.get("available_tags", [])
                ]

                channel_meta = ChannelMeta(
                    id=channel_id,
                    name=entry["name"],
                    guild=guild,
                    category_id=entry.get("category_id"),
                    category=category,
                    available_tags=tags,
                )
                new_channels[channel_id] = channel_meta
                new_guild_channels[guild.id][channel_id] = channel_meta

            self.indexed_channels = new_channels
            self.guild_channels = dict(new_guild_channels)
            logger.debug(f"从 Redis 加载了 {len(new_channels)} 个频道的元数据")
        except Exception:
            logger.error("从 Redis 加载频道元数据失败", exc_info=True)

    async def _periodic_sync(self):
        """定时轮询：每 60 秒从 Redis 刷新频道元数据，从 DB 刷新 BotConfig。"""
        while self._is_running:
            await asyncio.sleep(60)
            try:
                logger.debug("ApiCacheService 定时同步触发")
                await self._load_channel_metadata_from_redis()
                await self.refresh_bot_config_cache()
            except Exception:
                logger.error("ApiCacheService 定时同步失败", exc_info=True)
