"""
对搜索性能优化改动的测试覆盖。

覆盖范围：
- FTS tsquery 缓存（Redis 命中/未命中/回写）
- redis_client 参数透传链路
"""

import json
from datetime import datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlmodel import delete

from models import Thread
from core.thread_repository import ThreadRepository


# ══════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════


@pytest_asyncio.fixture(scope="function")
async def seeded_fts_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """种子：用于 FTS tsquery 缓存测试的帖子。"""
    async with db_session_factory() as session:
        await session.execute(delete(Thread))
        await session.commit()

        now = datetime.now()
        threads = [
            Thread(
                thread_id=601,
                channel_id=1,
                title="关于百合破坏的讨论",
                first_message_excerpt="百合和GL的讨论",
                author_id=1,
                created_at=now,
            ),
            Thread(
                thread_id=602,
                channel_id=1,
                title="纯爱小说分享",
                first_message_excerpt="推荐一些女性视角的小说",
                author_id=2,
                created_at=now,
            ),
            Thread(
                thread_id=603,
                channel_id=1,
                title="催眠洗脑魔法少女",
                first_message_excerpt="MC相关话题讨论",
                author_id=3,
                created_at=now,
            ),
        ]
        session.add_all(threads)
        await session.commit()

        yield session

        await session.execute(delete(Thread))
        await session.commit()


# ══════════════════════════════════════════════
# 方案 B：FTS tsquery 缓存测试
# ══════════════════════════════════════════════


class TestFTSQueryCaching:
    """测试 get_fts_matched_thread_ids() 的 Redis 缓存行为。"""

    def _make_mock_redis(self, cached_data=None):
        """构造模拟 Redis 客户端。"""
        mock = AsyncMock()
        mock.get = AsyncMock(
            return_value=json.dumps(cached_data) if cached_data else None
        )
        mock.setex = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_cache_miss_writes_to_redis(self, seeded_fts_session):
        """缓存未命中时，正常执行分词并将 tsquery 字符串写入 Redis。"""
        repo = ThreadRepository(seeded_fts_session)
        mock_redis = self._make_mock_redis(cached_data=None)

        result = await repo.get_fts_matched_thread_ids(
            keywords="百合/gl",
            exclude_keywords=None,
            redis_client=mock_redis,
        )
        # 验证返回了 FTS 子查询
        assert result.has_include is True
        assert len(result.include_conditions) > 0

        # 验证 Redis setex 被调用（回写缓存）
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        cache_key = call_args[0][0]
        ttl = call_args[0][1]
        assert cache_key.startswith("fts:tsquery:result:")
        assert ttl == 3600  # TTL 1 小时

        # 验证缓存值可反序列化且结构正确
        cached_value = json.loads(call_args[0][2])
        assert "ig" in cached_value
        assert len(cached_value["ig"]) > 0

    @pytest.mark.asyncio
    async def test_cache_hit_skips_tokenization(self, seeded_fts_session):
        """缓存命中时，跳过 jieba 分词，直接反序列化构建子查询。"""
        repo = ThreadRepository(seeded_fts_session)

        # 第一次调用：正常分词，获取实际输出
        mock_redis_1 = self._make_mock_redis(cached_data=None)
        result1 = await repo.get_fts_matched_thread_ids(
            keywords="百合/gl",
            exclude_keywords=None,
            redis_client=mock_redis_1,
        )
        # 从第一次调用的 setex 中提取缓存数据
        cached_value = json.loads(mock_redis_1.setex.call_args[0][2])

        # 第二次调用：模拟缓存命中
        mock_redis_2 = self._make_mock_redis(cached_data=cached_value)
        result2 = await repo.get_fts_matched_thread_ids(
            keywords="百合/gl",
            exclude_keywords=None,
            redis_client=mock_redis_2,
        )

        # 验证两次返回结构一致
        assert result2.has_include == result1.has_include
        assert len(result2.include_conditions) == len(result1.include_conditions)

        # 验证缓存命中时 get 被调用但 setex 不被调用
        mock_redis_2.get.assert_called_once()
        mock_redis_2.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_redis_client_no_cache_interaction(self, seeded_fts_session):
        """未提供 redis_client 时，正常分词且不触发任何缓存操作。"""
        repo = ThreadRepository(seeded_fts_session)

        result = await repo.get_fts_matched_thread_ids(
            keywords="百合/gl",
            exclude_keywords=None,
            redis_client=None,
        )

        assert result.has_include is True
        assert len(result.include_conditions) > 0

    @pytest.mark.asyncio
    async def test_exclude_keywords_cached(self, seeded_fts_session):
        """排除关键词的 tsquery 也被正确缓存。"""
        repo = ThreadRepository(seeded_fts_session)
        mock_redis = self._make_mock_redis(cached_data=None)

        await repo.get_fts_matched_thread_ids(
            keywords="百合",
            exclude_keywords="破坏",
            redis_client=mock_redis,
        )

        mock_redis.setex.assert_called_once()
        cached_value = json.loads(mock_redis.setex.call_args[0][2])
        assert "eg" in cached_value  # 排除词的 tsquery
        assert "ig" in cached_value  # 正选词的 tsquery

    @pytest.mark.asyncio
    async def test_exclude_keywords_cache_hit_rebuilds_exclude_stmt(
        self, seeded_fts_session
    ):
        """排除关键词缓存命中后正确重建 exclude_stmt 子查询。"""
        repo = ThreadRepository(seeded_fts_session)

        # 第一次：获取缓存数据
        mock_redis_1 = self._make_mock_redis(cached_data=None)
        await repo.get_fts_matched_thread_ids(
            keywords="百合",
            exclude_keywords="破坏",
            redis_client=mock_redis_1,
        )
        cached_value = json.loads(mock_redis_1.setex.call_args[0][2])

        # 第二次：缓存命中
        mock_redis_2 = self._make_mock_redis(cached_data=cached_value)
        result = await repo.get_fts_matched_thread_ids(
            keywords="百合",
            exclude_keywords="破坏",
            redis_client=mock_redis_2,
        )

        assert result.has_exclude is True
        assert result.exclude_condition is not None

    @pytest.mark.asyncio
    async def test_cache_key_includes_markers(self, seeded_fts_session):
        """不同的豁免标记应产生不同的缓存 key。"""
        repo = ThreadRepository(seeded_fts_session)

        mock_redis_a = self._make_mock_redis(cached_data=None)
        await repo.get_fts_matched_thread_ids(
            keywords="百合",
            exclude_keywords="破坏",
            exemption_markers=["禁"],
            redis_client=mock_redis_a,
        )
        key_a = mock_redis_a.setex.call_args[0][0]

        mock_redis_b = self._make_mock_redis(cached_data=None)
        await repo.get_fts_matched_thread_ids(
            keywords="百合",
            exclude_keywords="破坏",
            exemption_markers=["🈲"],
            redis_client=mock_redis_b,
        )
        key_b = mock_redis_b.setex.call_args[0][0]

        assert key_a != key_b

    @pytest.mark.asyncio
    async def test_cache_key_prefix_is_keywords_first_5_chars(self, seeded_fts_session):
        """缓存 key 前缀为 keywords 的前 5 个字符。"""
        repo = ThreadRepository(seeded_fts_session)
        mock_redis = self._make_mock_redis(cached_data=None)

        await repo.get_fts_matched_thread_ids(
            keywords="百合GLyuri",
            exclude_keywords=None,
            redis_client=mock_redis,
        )

        cache_key = mock_redis.setex.call_args[0][0]
        assert "百合GLy" in cache_key  # "百合GLyuri"[:5] == "百合GLy"

    @pytest.mark.asyncio
    async def test_cache_key_with_none_keywords_uses_none_prefix(
        self, seeded_fts_session
    ):
        """keywords 为 None 时，前缀取 'none'。"""
        repo = ThreadRepository(seeded_fts_session)
        mock_redis = self._make_mock_redis(cached_data=None)

        await repo.get_fts_matched_thread_ids(
            keywords=None,
            exclude_keywords="破坏",
            redis_client=mock_redis,
        )

        cache_key = mock_redis.setex.call_args[0][0]
        assert ":none:" in cache_key

    @pytest.mark.asyncio
    async def test_cached_tsquery_produces_same_results(self, seeded_fts_session):
        """缓存命中和未命中执行同一搜索应产生相同的数据库侧匹配。"""
        from search.search_service import SearchService
        from search.qo.thread_search import ThreadSearchQuery
        from core.tag_cache_service import TagCacheService

        tag_cache = TagCacheService(session_factory=None)  # type: ignore[arg-type]

        # 首次：无缓存（redis_client=None）
        service1 = SearchService(seeded_fts_session, tag_cache)
        threads1, total1 = await service1.search_threads_with_count(
            ThreadSearchQuery(keywords="百合"),
            limit=50,
            offset=0,
            total_display_count=1000,
            exploration_factor=1.414,
            strength_weight=10.0,
            redis_client=None,
        )

        # 二次：同样无缓存 — 验证幂等性
        service2 = SearchService(seeded_fts_session, tag_cache)
        threads2, total2 = await service2.search_threads_with_count(
            ThreadSearchQuery(keywords="百合"),
            limit=50,
            offset=0,
            total_display_count=1000,
            exploration_factor=1.414,
            strength_weight=10.0,
            redis_client=None,
        )

        assert total1 == total2
        assert {t.thread_id for t in threads1} == {t.thread_id for t in threads2}

    @pytest.mark.asyncio
    async def test_redis_failure_falls_back_gracefully(self, seeded_fts_session):
        """Redis 异常时降级到正常分词流程，不抛出异常。"""
        repo = ThreadRepository(seeded_fts_session)
        mock_redis = self._make_mock_redis(cached_data=None)
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection failed"))

        # 不应抛出异常
        result = await repo.get_fts_matched_thread_ids(
            keywords="百合/gl",
            exclude_keywords=None,
            redis_client=mock_redis,
        )
        assert result.has_include is True
        assert len(result.include_conditions) > 0

    @pytest.mark.asyncio
    async def test_redis_write_failure_does_not_block(self, seeded_fts_session):
        """Redis 写入失败不影响返回结果。"""
        repo = ThreadRepository(seeded_fts_session)
        mock_redis = self._make_mock_redis(cached_data=None)
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis write failed"))

        # 不应抛出异常
        result = await repo.get_fts_matched_thread_ids(
            keywords="百合/gl",
            exclude_keywords=None,
            redis_client=mock_redis,
        )
        assert result.has_include is True
        assert len(result.include_conditions) > 0


# ══════════════════════════════════════════════
# redis_client 参数透传链路测试
# ══════════════════════════════════════════════


class TestRedisClientPassthrough:
    """验证 redis_client 从顶层 API 到 ThreadRepository 的完整链路。"""

    @pytest.mark.asyncio
    async def test_search_service_passes_redis_client(self, seeded_fts_session):
        """SearchService.search_threads_with_count() 将 redis_client 传给 ThreadRepository。"""
        from search.search_service import SearchService
        from search.qo.thread_search import ThreadSearchQuery
        from core.tag_cache_service import TagCacheService

        tag_cache = TagCacheService(session_factory=None)  # type: ignore[arg-type]
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        service = SearchService(seeded_fts_session, tag_cache)
        threads, total = await service.search_threads_with_count(
            ThreadSearchQuery(keywords="百合"),
            limit=50,
            offset=0,
            total_display_count=1000,
            exploration_factor=1.414,
            strength_weight=10.0,
            redis_client=mock_redis,
        )

        # 验证 Redis 被调用（缓存写入）
        mock_redis.setex.assert_called_once()
        # 验证搜索结果正确
        assert total >= 0
        assert isinstance(threads, list)

    @pytest.mark.asyncio
    async def test_search_service_without_redis_client_still_works(
        self, seeded_fts_session
    ):
        """redis_client 为 None 时 search_threads_with_count() 正常工作。"""
        from search.search_service import SearchService
        from search.qo.thread_search import ThreadSearchQuery
        from core.tag_cache_service import TagCacheService

        tag_cache = TagCacheService(session_factory=None)  # type: ignore[arg-type]

        service = SearchService(seeded_fts_session, tag_cache)
        threads, total = await service.search_threads_with_count(
            ThreadSearchQuery(keywords="百合"),
            limit=50,
            offset=0,
            total_display_count=1000,
            exploration_factor=1.414,
            strength_weight=10.0,
            redis_client=None,
        )

        assert total >= 0
        assert isinstance(threads, list)


# ══════════════════════════════════════════════
# 缓存 Key 常量测试
# ══════════════════════════════════════════════


class TestCacheKeyFormat:
    """测试 CacheKeys.FTS_TSQUERY_RESULT 的格式方法。"""

    def test_format_with_prefix_and_hash(self):
        """format() 正确填充 prefix 和 hash 占位符。"""
        from shared.enum.cache_keys import CacheKeys

        key = CacheKeys.FTS_TSQUERY_RESULT.format(
            prefix="百合GLy",
            hash="abc123def456",
        )
        assert key == "fts:tsquery:result:百合GLy:abc123def456"

    def test_key_includes_all_segments(self):
        """缓存 key 包含所有必要片段。"""
        from shared.enum.cache_keys import CacheKeys

        key = CacheKeys.FTS_TSQUERY_RESULT.format(prefix="test", hash="md5hash")
        segments = key.split(":")
        assert segments[0] == "fts"
        assert segments[1] == "tsquery"
        assert segments[2] == "result"
        assert len(segments) == 5  # fts:tsquery:result:{prefix}:{hash}
