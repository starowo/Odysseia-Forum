"""Redis 趋势频道日榜和范围聚合测试。"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from core.redis_trend_service import RedisTrendService


async def _delete_metric_keys(redis_client, metric: str) -> None:
    """删除单个测试指标创建的全部 Redis 键。"""
    keys = [key async for key in redis_client.scan_iter(match=f"*{metric}*", count=100)]
    if keys:
        await redis_client.delete(*keys)


@pytest.mark.asyncio
async def test_record_increment_writes_global_and_channel_daily_keys(redis_client):
    """单次趋势增量同时写入全局榜和频道榜并设置 TTL。"""
    metric = f"test_dual_write_{uuid4().hex}"
    service = RedisTrendService()
    now = datetime.now(timezone.utc)

    try:
        await service.record_increment(metric, 101, 2001, count=3)
        global_key = service._get_daily_key(metric, now)
        channel_key = service._get_channel_daily_key(metric, now, 2001)

        assert await redis_client.zscore(global_key, "101") == 3
        assert await redis_client.zscore(channel_key, "101") == 3
        assert await redis_client.ttl(global_key) > 0
        assert await redis_client.ttl(channel_key) > 0
    finally:
        await _delete_metric_keys(redis_client, metric)


@pytest.mark.asyncio
async def test_channel_scope_uses_max_and_handles_empty_channels(redis_client):
    """多频道子榜保持趋势顺序，并以 MAX 防止异常重复成员翻倍。"""
    metric = f"test_scope_{uuid4().hex}"
    service = RedisTrendService()
    now = datetime.now(timezone.utc)

    try:
        await redis_client.zadd(
            service._get_channel_daily_key(metric, now, 1),
            {"101": 5, "103": 2},
        )
        await redis_client.zadd(
            service._get_channel_daily_key(metric, now, 2),
            {"102": 4, "103": 7},
        )

        result = await service.get_top_surging_ids(
            metric, days=1, limit=10, channel_ids=[2, 1, 2]
        )
        empty_result = await service.get_top_surging_ids(
            metric, days=1, limit=10, channel_ids=[999]
        )

        assert result == [103, 101, 102]
        assert empty_result == []
    finally:
        await _delete_metric_keys(redis_client, metric)
