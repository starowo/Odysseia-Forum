import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from dto.search import SimilarThreadCandidateDTO, SimilarThreadCandidatePoolDTO
from search.similar_threads_busy_error import SimilarThreadsBusyError
from search.similar_threads_cache_service import SimilarThreadsCacheService
from shared.similar_threads_cache import (
    get_similar_candidates_cache_key,
    invalidate_similar_candidate_pools,
)


def _candidate(thread_id: int = 100, matched_tag_count: int = 2):
    """构造候选 DTO。"""
    return SimilarThreadCandidateDTO(
        thread_id=thread_id,
        matched_tag_count=matched_tag_count,
    )


@pytest.mark.asyncio
async def test_complete_candidate_pool_uses_three_hour_ttl():
    """完整非空候选池缓存三小时。"""
    redis = AsyncMock()
    redis.get.return_value = None
    service = SimilarThreadsCacheService(redis)
    builder = AsyncMock(return_value=([_candidate()], True))

    pool = await service.get_or_build(42, False, builder)

    assert [item.thread_id for item in pool.candidates] == [100]
    redis.setex.assert_awaited_once()
    assert redis.setex.await_args.args[1] == 3 * 60 * 60
    await service.close()


@pytest.mark.asyncio
async def test_complete_empty_pool_uses_ten_minute_ttl():
    """完整空候选池缓存十分钟。"""
    redis = AsyncMock()
    redis.get.return_value = None
    service = SimilarThreadsCacheService(redis)

    await service.get_or_build(42, False, AsyncMock(return_value=([], True)))

    assert redis.setex.await_args.args[1] == 10 * 60
    await service.close()


@pytest.mark.asyncio
async def test_partial_candidate_pool_is_not_cached():
    """超时产生的部分候选仅服务当前请求。"""
    redis = AsyncMock()
    redis.get.return_value = None
    service = SimilarThreadsCacheService(redis)

    pool = await service.get_or_build(
        42,
        False,
        AsyncMock(return_value=([_candidate()], False)),
    )

    assert len(pool.candidates) == 1
    redis.setex.assert_not_awaited()
    await service.close()


@pytest.mark.asyncio
async def test_same_key_requests_share_one_cold_build():
    """相同 Key 的并发硬未命中只执行一次 builder。"""
    redis = AsyncMock()
    redis.get.return_value = None
    service = SimilarThreadsCacheService(redis)
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def builder():
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return [_candidate()], True

    first = asyncio.create_task(service.get_or_build(42, False, builder))
    await started.wait()
    second = asyncio.create_task(service.get_or_build(42, False, builder))
    await asyncio.sleep(0)
    release.set()
    first_pool, second_pool = await asyncio.gather(first, second)

    assert calls == 1
    assert first_pool == second_pool
    await service.close()


@pytest.mark.asyncio
async def test_soft_expired_pool_returns_immediately_and_refreshes():
    """软过期命中先返回旧池，再在后台刷新。"""
    redis = AsyncMock()
    cached = SimilarThreadCandidatePoolDTO(
        generated_at=time.time() - SimilarThreadsCacheService.SOFT_REFRESH_SECONDS - 1,
        candidates=[_candidate(100)],
    )
    redis.get.return_value = cached.model_dump_json()
    service = SimilarThreadsCacheService(redis)
    refreshed = asyncio.Event()

    async def builder():
        refreshed.set()
        return [_candidate(200)], True

    returned = await service.get_or_build(42, False, builder)
    await asyncio.wait_for(refreshed.wait(), timeout=1)
    await asyncio.sleep(0)

    assert returned.candidates[0].thread_id == 100
    assert redis.setex.await_args.args[1] == 3 * 60 * 60
    await service.close()


@pytest.mark.asyncio
async def test_failed_soft_refresh_keeps_old_pool_and_can_retry():
    """后台刷新失败不影响旧池，后续命中仍可再次尝试。"""
    redis = AsyncMock()
    cached = SimilarThreadCandidatePoolDTO(
        generated_at=time.time() - SimilarThreadsCacheService.SOFT_REFRESH_SECONDS - 1,
        candidates=[_candidate(100)],
    )
    redis.get.return_value = cached.model_dump_json()
    service = SimilarThreadsCacheService(redis)
    attempts = 0
    attempted = asyncio.Event()

    async def builder():
        nonlocal attempts
        attempts += 1
        attempted.set()
        raise RuntimeError("refresh failed")

    first = await service.get_or_build(42, False, builder)
    await asyncio.wait_for(attempted.wait(), timeout=1)
    await asyncio.sleep(0)
    attempted.clear()
    second = await service.get_or_build(42, False, builder)
    await asyncio.wait_for(attempted.wait(), timeout=1)

    assert first.candidates[0].thread_id == 100
    assert second.candidates[0].thread_id == 100
    assert attempts == 2
    redis.setex.assert_not_awaited()
    await service.close()


@pytest.mark.asyncio
async def test_distinct_cold_build_fails_fast_when_capacity_is_full():
    """不同 Key 的冷构建不会无限排队占用请求。"""
    redis = AsyncMock()
    redis.get.return_value = None
    service = SimilarThreadsCacheService(redis, cold_query_concurrency=1)
    service.COLD_QUERY_WAIT_SECONDS = 0.01
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocking_builder():
        started.set()
        await release.wait()
        return [_candidate()], True

    first = asyncio.create_task(service.get_or_build(1, False, blocking_builder))
    await started.wait()
    with pytest.raises(SimilarThreadsBusyError):
        await service.get_or_build(
            2,
            False,
            AsyncMock(return_value=([_candidate(200)], True)),
        )
    release.set()
    await first
    await service.close()


@pytest.mark.asyncio
async def test_invalidation_deletes_both_permission_pools():
    """源帖变化时同时失效普通区与深渊区候选池。"""
    redis = AsyncMock()

    await invalidate_similar_candidate_pools(redis, 42)

    redis.delete.assert_awaited_once_with(
        get_similar_candidates_cache_key(42, include_abyss=False),
        get_similar_candidates_cache_key(42, include_abyss=True),
    )
