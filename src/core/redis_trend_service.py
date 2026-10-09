import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from uuid import uuid4

from shared.enum import ConstantEnum
from shared.redis_client import RedisManager


class RedisTrendService:
    """处理基于 Redis 的趋势记录、聚合缓存和频道范围查询。"""

    EMPTY_MEMBER = "-1"
    _ignored_channel_ids: frozenset[int] = frozenset()

    @classmethod
    def configure_ignored_channels(cls, channel_ids: Iterable[int | str]) -> list[int]:
        """设置本进程不参与趋势统计的频道并返回规范化列表。"""
        cls._ignored_channel_ids = frozenset(
            int(channel_id)
            for channel_id in channel_ids
            if isinstance(channel_id, (int, str))
            and str(channel_id).strip().lstrip("-").isdigit()
        )
        return sorted(cls._ignored_channel_ids)

    def _get_daily_key(self, metric: str, dt: datetime) -> str:
        """格式化全局日榜 Redis 键名。"""
        date_str = dt.strftime("%Y%m%d")
        return f"trend:{metric}:{date_str}"

    def _get_channel_daily_key(self, metric: str, dt: datetime, channel_id: int) -> str:
        """格式化频道日榜 Redis 键名。"""
        return f"{self._get_daily_key(metric, dt)}:channel:{channel_id}"

    def _get_global_cache_key(self, metric: str, days: int) -> str:
        """格式化全局趋势聚合缓存键名。"""
        return f"cache:surge:{metric}:{days}"

    def _get_channel_cache_key(self, metric: str, days: int, channel_id: int) -> str:
        """格式化单频道跨天趋势聚合缓存键名。"""
        return f"cache:surge:{metric}:{days}:channel:{channel_id}"

    def _get_channel_scope_cache_key(
        self, metric: str, days: int, channel_ids: list[int]
    ) -> str:
        """为排序去重后的频道范围生成长度固定的聚合缓存键。"""
        raw_scope = ",".join(str(channel_id) for channel_id in channel_ids)
        scope_hash = hashlib.sha256(raw_scope.encode("utf-8")).hexdigest()[:20]
        return f"cache:surge:{metric}:{days}:channels:{scope_hash}"

    async def record_increment(
        self,
        metric: str,
        thread_id: int,
        channel_id: int,
        count: int = 1,
    ) -> None:
        """为非屏蔽频道记录全局和频道趋势增量，并将日榜保留九十天。"""
        if count <= 0 or channel_id in self._ignored_channel_ids:
            return

        redis = RedisManager.get_client()
        now = datetime.now(timezone.utc)
        global_key = self._get_daily_key(metric, now)
        channel_key = self._get_channel_daily_key(metric, now, channel_id)
        ttl_seconds = 86400 * ConstantEnum.MAX_SURGE_DAYS.value

        # 全局榜用于无频道筛选和回滚，频道榜用于直接构建筛选后的趋势子榜。
        async with redis.pipeline(transaction=True) as pipeline:
            pipeline.zincrby(global_key, count, str(thread_id))
            pipeline.expire(global_key, ttl_seconds)
            pipeline.zincrby(channel_key, count, str(thread_id))
            pipeline.expire(channel_key, ttl_seconds)
            await pipeline.execute()

    async def get_top_surging_ids(
        self,
        metric: str,
        days: int,
        limit: int,
        offset: int = 0,
        channel_ids: Optional[list[int]] = None,
    ) -> list[int]:
        """按全局或频道范围读取趋势排名，并使用短效聚合缓存。"""
        redis = RedisManager.get_client()

        if channel_ids is not None:
            normalized_channel_ids = sorted(set(channel_ids))
            if not normalized_channel_ids:
                return []

            cache_key = await self._get_or_build_channel_scope_cache(
                metric, days, normalized_channel_ids
            )
        else:
            cache_key = await self._get_or_build_global_cache(metric, days)

        if not cache_key:
            return []

        top_items = await redis.zrevrange(cache_key, offset, offset + limit - 1)
        return [int(item) for item in top_items if item != self.EMPTY_MEMBER]

    async def _get_or_build_global_cache(self, metric: str, days: int) -> Optional[str]:
        """获取或构建指定指标的全局跨天趋势缓存。"""
        now = datetime.now(timezone.utc)
        source_keys = [
            self._get_daily_key(metric, now - timedelta(days=index))
            for index in range(days)
        ]
        cache_key = self._get_global_cache_key(metric, days)
        return await self._get_or_build_aggregate_cache(
            cache_key, source_keys, aggregate="SUM"
        )

    async def _get_or_build_channel_scope_cache(
        self, metric: str, days: int, channel_ids: list[int]
    ) -> Optional[str]:
        """获取或构建多频道趋势子榜缓存。"""
        channel_cache_keys = await asyncio.gather(
            *[
                self._get_or_build_channel_cache(metric, days, channel_id)
                for channel_id in channel_ids
            ]
        )
        if any(cache_key is None for cache_key in channel_cache_keys):
            return None

        scope_cache_key = self._get_channel_scope_cache_key(metric, days, channel_ids)
        return await self._get_or_build_aggregate_cache(
            scope_cache_key,
            [cache_key for cache_key in channel_cache_keys if cache_key],
            aggregate="MAX",
        )

    async def _get_or_build_channel_cache(
        self, metric: str, days: int, channel_id: int
    ) -> Optional[str]:
        """获取或构建单频道跨天趋势缓存。"""
        now = datetime.now(timezone.utc)
        source_keys = [
            self._get_channel_daily_key(metric, now - timedelta(days=index), channel_id)
            for index in range(days)
        ]
        cache_key = self._get_channel_cache_key(metric, days, channel_id)
        return await self._get_or_build_aggregate_cache(
            cache_key, source_keys, aggregate="SUM"
        )

    async def _get_or_build_aggregate_cache(
        self,
        cache_key: str,
        source_keys: list[str],
        aggregate: str,
    ) -> Optional[str]:
        """在分布式锁保护下构建 ZSET 聚合缓存。"""
        redis = RedisManager.get_client()
        if await redis.exists(cache_key):
            return cache_key

        lock_key = f"lock:{cache_key}"
        lock_token = uuid4().hex
        acquired = await redis.set(lock_key, lock_token, ex=30, nx=True)
        if acquired:
            try:
                # 跨天聚合使用 SUM，多频道合并使用 MAX，避免异常重复成员翻倍。
                await redis.zunionstore(cache_key, source_keys, aggregate=aggregate)
                if await redis.zcard(cache_key) == 0:
                    await redis.zadd(cache_key, {self.EMPTY_MEMBER: 0})
                await redis.expire(
                    cache_key, ConstantEnum.TREND_CACHE_EXPIRE_SECONDS.value
                )
                return cache_key
            finally:
                await self._release_lock(lock_key, lock_token)

        # 未获得锁时等待其他进程完成聚合，避免并发重复计算。
        for _ in range(20):
            await asyncio.sleep(0.15)
            if await redis.exists(cache_key):
                return cache_key

        return None

    async def _release_lock(self, lock_key: str, lock_token: str) -> None:
        """仅由当前缓存构建者释放分布式锁。"""
        redis = RedisManager.get_client()
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        end
        return 0
        """
        await redis.eval(script, 1, lock_key, lock_token)
