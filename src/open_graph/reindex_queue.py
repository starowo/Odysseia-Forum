from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from redis.asyncio import Redis


logger = logging.getLogger(__name__)

FINISH_SUCCESS_SCRIPT = """
redis.call('set', KEYS[1], ARGV[1], 'EX', ARGV[3])
if redis.call('get', KEYS[2]) == ARGV[2] then
    redis.call('set', KEYS[3], '1', 'EX', ARGV[4])
    redis.call('del', KEYS[2])
end
return 1
"""
FINISH_FAILURE_SCRIPT = """
redis.call('set', KEYS[1], ARGV[1], 'EX', ARGV[3])
if redis.call('get', KEYS[2]) == ARGV[2] then
    redis.call('del', KEYS[2])
end
return 1
"""


class OpenGraphReindexQueue:
    """使用 Redis 协调 API 请求与 Bot 重索引结果。"""

    QUEUE_KEY = "open_graph:reindex_queue"
    PENDING_TTL_SECONDS = 300
    RESULT_TTL_SECONDS = 300
    COOLDOWN_TTL_SECONDS = 3600
    POLL_INTERVAL_SECONDS = 0.1

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_or_enqueue(self, thread_id: int) -> str | None:
        """复用现有 pending 任务，或取得所有权后创建新任务。"""
        pending_key = f"pending:{thread_id}"
        existing_job_id = await self.redis.get(pending_key)
        if existing_job_id:
            logger.debug(
                "复用 OG pending 任务",
                extra={"thread_id": thread_id, "job_id": str(existing_job_id)},
            )
            return str(existing_job_id)

        if await self.redis.exists(f"cooldown:{thread_id}"):
            return None

        job_id = uuid.uuid4().hex
        acquired = await self.redis.set(
            pending_key,
            job_id,
            nx=True,
            ex=self.PENDING_TTL_SECONDS,
        )
        if not acquired:
            existing_job_id = await self.redis.get(pending_key)
            return str(existing_job_id) if existing_job_id else None

        payload = json.dumps(
            {"job_id": job_id, "thread_id": str(thread_id)},
            separators=(",", ":"),
        )
        try:
            await self.redis.lpush(self.QUEUE_KEY, payload)
        except Exception:
            delete_if_owned_script = (
                "if redis.call('get', KEYS[1]) == ARGV[1] then "
                "return redis.call('del', KEYS[1]) end return 0"
            )
            await self.redis.eval(
                delete_if_owned_script, 1, f"pending:{thread_id}", job_id
            )
            raise
        try:
            queue_depth = await self.redis.llen(self.QUEUE_KEY)
        except Exception:
            queue_depth = -1
            logger.debug("读取 OG 队列深度失败", exc_info=True)
        logger.info(
            "OG 重索引任务已入队",
            extra={
                "thread_id": thread_id,
                "job_id": job_id,
                "queue_depth": queue_depth,
            },
        )
        return job_id

    async def wait_for_result(
        self, job_id: str, timeout_seconds: float
    ) -> dict[str, Any] | None:
        """轮询持久化结果键，使多个等待者都可读取同一结果。"""
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        result_key = f"result:{job_id}"
        while True:
            raw_result = await self.redis.get(result_key)
            if raw_result:
                try:
                    result = json.loads(raw_result)
                except (TypeError, json.JSONDecodeError):
                    logger.warning("OG 重索引结果格式无效", extra={"job_id": job_id})
                    return None
                logger.info(
                    "OG 重索引等待完成",
                    extra={
                        "job_id": job_id,
                        "status": result.get("status")
                        if isinstance(result, dict)
                        else "invalid",
                        "elapsed_ms": int(
                            (timeout_seconds - max(0.0, deadline - time.monotonic()))
                            * 1000
                        ),
                    },
                )
                return result if isinstance(result, dict) else None

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "OG 重索引等待超时",
                    extra={"job_id": job_id, "timeout_seconds": timeout_seconds},
                )
                return None
            await asyncio.sleep(min(self.POLL_INTERVAL_SECONDS, remaining))

    async def pop_job(self, timeout_seconds: int = 5) -> dict[str, Any] | None:
        """阻塞读取一个重索引任务并校验基础字段。"""
        item = await self.redis.brpop(self.QUEUE_KEY, timeout=timeout_seconds)
        if not item:
            return None
        try:
            payload = json.loads(item[1])
            job_id = str(payload["job_id"])
            thread_id = int(payload["thread_id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning("丢弃格式无效的 OG 重索引任务")
            return None
        return {"job_id": job_id, "thread_id": thread_id}

    async def finish_success(self, job_id: str, thread_id: int) -> None:
        """写入成功结果，并仅在任务仍属当前 job 时设置冷却和清理 pending。"""
        result = json.dumps(
            {"status": "success", "thread_id": str(thread_id)},
            separators=(",", ":"),
        )
        await self.redis.eval(
            FINISH_SUCCESS_SCRIPT,
            3,
            f"result:{job_id}",
            f"pending:{thread_id}",
            f"cooldown:{thread_id}",
            result,
            job_id,
            self.RESULT_TTL_SECONDS,
            self.COOLDOWN_TTL_SECONDS,
        )

    async def finish_failure(
        self, job_id: str, thread_id: int, error_code: str
    ) -> None:
        """写入脱敏失败码，并清理当前任务的 pending。"""
        result = json.dumps(
            {
                "status": "failed",
                "thread_id": str(thread_id),
                "error_code": error_code,
            },
            separators=(",", ":"),
        )
        await self.redis.eval(
            FINISH_FAILURE_SCRIPT,
            2,
            f"result:{job_id}",
            f"pending:{thread_id}",
            result,
            job_id,
            self.RESULT_TTL_SECONDS,
        )
