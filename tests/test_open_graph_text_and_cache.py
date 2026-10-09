import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from dto.open_graph import (
    OpenGraphAuthorDTO,
    ThreadShareMetadataDTO,
    ThreadShareStatsDTO,
)
from open_graph.metadata_cache import OpenGraphMetadataCache
from open_graph.text_formatter import OpenGraphTextFormatter


def test_text_formatter_cleans_html_markdown_entities_and_whitespace():
    """文本清洗保留链接标签与图片 alt，同时移除 HTML 和 Markdown 控制符。"""
    value = "  <b>标题</b> &amp; [标签](https://example.com) ![封面](x.png) **重点**\n "

    result = OpenGraphTextFormatter.format(value, limit=200, empty_value=None)

    assert result == "标题 & 标签 封面 重点"


def test_text_formatter_applies_placeholders_and_inclusive_ellipsis_limits():
    """空文本使用统一占位词，截断后的省略号计入字符上限。"""
    assert (
        OpenGraphTextFormatter.format("<br> ** ", limit=40, empty_value="未命名")
        == "未命名"
    )
    assert OpenGraphTextFormatter.format("123456", limit=5, empty_value=None) == "1234…"
    assert (
        len(OpenGraphTextFormatter.format("x" * 201, limit=200, empty_value=None))
        == 200
    )


@pytest.mark.asyncio
async def test_metadata_cache_clips_ttl_and_keeps_internal_sources_out_of_payload():
    """缓存 TTL 按图片安全窗口裁剪，内部来源 ID 不进入公开响应。"""
    redis = MagicMock()
    redis.set = AsyncMock()
    cache = OpenGraphMetadataCache(redis, ttl_seconds=600)
    metadata = ThreadShareMetadataDTO(
        title="帖子",
        author=OpenGraphAuthorDTO(display_name="作者"),
        stats=ThreadShareStatsDTO(reaction_count=1, reply_count=2, collection_count=3),
        created_at=datetime(2026, 8, 8),
        updated_at=datetime(2026, 8, 8),
    )

    await cache.set("thread", 42, metadata, [42], ttl_limit_seconds=120)

    call = redis.set.await_args
    assert call.args[0] == "open_graph:metadata:v2:thread:42"
    assert call.kwargs["ex"] == 120
    envelope = json.loads(call.args[1])
    assert envelope["source_thread_ids"] == [42]
    assert "thread_id" not in envelope["payload"]
    assert envelope["payload"]["created_at"].endswith("Z")


@pytest.mark.asyncio
async def test_metadata_cache_hit_and_redis_failure_are_safe():
    """有效缓存可恢复 DTO，Redis 读取故障则按未命中降级。"""
    payload = {
        "payload": {
            "title": "帖子",
            "description": None,
            "image_url": None,
            "author": {"display_name": "作者", "avatar_url": None},
            "stats": {
                "reaction_count": 1,
                "reply_count": 2,
                "collection_count": 3,
            },
            "created_at": "2026-08-08T00:00:00Z",
            "updated_at": "2026-08-08T00:00:00Z",
        },
        "source_thread_ids": [42],
    }
    redis = MagicMock()
    redis.get = AsyncMock(return_value=json.dumps(payload))
    cache = OpenGraphMetadataCache(redis)

    hit = await cache.get("thread", 42, ThreadShareMetadataDTO)
    redis.get = AsyncMock(side_effect=ConnectionError("redis unavailable"))
    miss = await cache.get("thread", 42, ThreadShareMetadataDTO)

    assert hit is not None and hit[0].title == "帖子" and hit[1] == [42]
    assert miss is None


@pytest.mark.asyncio
async def test_metadata_cache_round_trip_with_real_redis(redis_client):
    """真实 Redis 可按 v2 键格式保存并供多个读取者恢复相同缓存信封。"""
    resource_id = uuid4().int
    cache_key = f"open_graph:metadata:v2:thread:{resource_id}"
    cache = OpenGraphMetadataCache(redis_client, ttl_seconds=600)
    metadata = ThreadShareMetadataDTO(
        title="Redis 帖子",
        author=OpenGraphAuthorDTO(display_name="作者"),
        stats=ThreadShareStatsDTO(reaction_count=1, reply_count=2, collection_count=3),
        created_at=datetime(2026, 8, 8),
        updated_at=datetime(2026, 8, 8),
    )

    try:
        await cache.set("thread", resource_id, metadata, [42], ttl_limit_seconds=5)
        first = await cache.get("thread", resource_id, ThreadShareMetadataDTO)
        second = await cache.get("thread", resource_id, ThreadShareMetadataDTO)
        ttl = await redis_client.ttl(cache_key)

        assert first is not None and second is not None
        assert first[0] == second[0] and first[1] == second[1] == [42]
        assert 1 <= ttl <= 5
    finally:
        await redis_client.delete(cache_key)
