import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from dto.open_graph import ThreadSyncResult
from open_graph.reindex_consumer import OpenGraphReindexConsumer
from open_graph.reindex_queue import OpenGraphReindexQueue


@pytest.mark.asyncio
async def test_pending_job_is_reused_without_duplicate_enqueue():
    """已有 pending 时所有请求复用同一 job_id。"""
    state = {}

    async def get_value(key):
        return state.get(key)

    async def set_value(key, value, *, nx, ex):
        assert nx is True
        assert ex == 300
        if key in state:
            return False
        state[key] = value
        return True

    redis = MagicMock()
    redis.get = AsyncMock(side_effect=get_value)
    redis.exists = AsyncMock(return_value=0)
    redis.set = AsyncMock(side_effect=set_value)
    redis.lpush = AsyncMock()
    redis.llen = AsyncMock(return_value=1)
    queue = OpenGraphReindexQueue(redis)

    created_job = await queue.get_or_enqueue(42)
    reused_job = await queue.get_or_enqueue(42)

    assert created_job is not None
    assert reused_job == created_job
    redis.lpush.assert_awaited_once()


@pytest.mark.asyncio
async def test_expired_pending_allows_a_new_job_to_be_enqueued():
    """模拟五分钟 TTL 到期后，后续请求可以重新取得任务所有权。"""
    state = {}

    async def get_value(key):
        return state.get(key)

    async def set_value(key, value, *, nx, ex):
        if key in state:
            return False
        assert nx is True and ex == 300
        state[key] = value
        return True

    redis = MagicMock()
    redis.get = AsyncMock(side_effect=get_value)
    redis.exists = AsyncMock(return_value=0)
    redis.set = AsyncMock(side_effect=set_value)
    redis.lpush = AsyncMock()
    redis.llen = AsyncMock(return_value=1)
    queue = OpenGraphReindexQueue(redis)

    first_job = await queue.get_or_enqueue(42)
    state.clear()
    second_job = await queue.get_or_enqueue(42)

    assert first_job != second_job
    assert redis.lpush.await_count == 2


@pytest.mark.asyncio
async def test_multiple_waiters_can_read_same_persistent_result():
    """结果键可由多个等待者读取而不会丢消息。"""
    redis = MagicMock()
    redis.get = AsyncMock(
        return_value=json.dumps({"status": "success", "thread_id": "42"})
    )
    queue = OpenGraphReindexQueue(redis)

    first, second = await asyncio.gather(
        queue.wait_for_result("job", 2),
        queue.wait_for_result("job", 2),
    )

    assert first == second == {"status": "success", "thread_id": "42"}


@pytest.mark.asyncio
async def test_success_finish_atomically_includes_result_cooldown_and_pending():
    """成功收尾脚本同时操作结果、冷却和 pending 三个键。"""
    redis = MagicMock()
    redis.eval = AsyncMock()
    queue = OpenGraphReindexQueue(redis)

    await queue.finish_success("job", 42)

    call_args = redis.eval.await_args.args
    assert call_args[1:5] == (3, "result:job", "pending:42", "cooldown:42")
    assert json.loads(call_args[5]) == {"status": "success", "thread_id": "42"}
    assert call_args[-2:] == (300, 3600)


@pytest.mark.asyncio
async def test_failure_finish_does_not_set_cooldown():
    """失败收尾只写结果并清理 pending，不携带 cooldown 键。"""
    redis = MagicMock()
    redis.eval = AsyncMock()
    queue = OpenGraphReindexQueue(redis)

    await queue.finish_failure("job", 42, "database_failed")

    call_args = redis.eval.await_args.args
    assert call_args[1:4] == (2, "result:job", "pending:42")
    assert "cooldown:42" not in call_args
    assert json.loads(call_args[4]) == {
        "status": "failed",
        "thread_id": "42",
        "error_code": "database_failed",
    }
    assert call_args[-1] == 300


@pytest.mark.asyncio
async def test_consumer_writes_success_only_after_sync_returns_success():
    """Bot 同步明确成功后才写成功结果。"""
    sync_service = MagicMock()
    sync_service.sync_thread = AsyncMock(return_value=ThreadSyncResult(success=True))
    queue = MagicMock()
    queue.finish_success = AsyncMock()
    queue.finish_failure = AsyncMock()
    consumer = OpenGraphReindexConsumer(sync_service, queue)

    await consumer._process_job("job", 42)

    sync_service.sync_thread.assert_awaited_once_with(42, priority=5)
    queue.finish_success.assert_awaited_once_with("job", 42)
    queue.finish_failure.assert_not_awaited()


@pytest.mark.asyncio
async def test_consumer_publishes_sanitized_failure_code():
    """同步失败仅写入稳定失败码。"""
    sync_service = MagicMock()
    sync_service.sync_thread = AsyncMock(
        return_value=ThreadSyncResult(success=False, error_code="database_failed")
    )
    queue = MagicMock()
    queue.finish_success = AsyncMock()
    queue.finish_failure = AsyncMock()
    consumer = OpenGraphReindexConsumer(sync_service, queue)

    await consumer._process_job("job", 42)

    queue.finish_failure.assert_awaited_once_with("job", 42, "database_failed")
    queue.finish_success.assert_not_awaited()
