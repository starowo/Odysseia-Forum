import logging
from datetime import datetime, time, timedelta, timezone

from redis.asyncio import Redis

from dto.update_detector import TokenEstimate, UpdateDetectionResult

logger = logging.getLogger(__name__)


class TokenStatsService:
    """按 UTC 日期将更新检测 Token 统计写入 Redis Hash。"""

    RETENTION_DAYS = 90
    KEY_PREFIX = "update_detector:token_stats"

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def record_estimate(
        self,
        model: str,
        thinking_enabled: bool,
        max_output_tokens: int,
        estimate: TokenEstimate,
    ) -> None:
        """累计一次本地估算数据。"""
        increments = {
            "eligible_request_count": 1,
            "ascii_character_count": estimate.ascii_character_count,
            "non_ascii_character_count": estimate.non_ascii_character_count,
            "estimated_content_tokens": estimate.estimated_content_tokens,
            "chat_overhead_tokens": estimate.chat_overhead_tokens,
            "estimated_prompt_tokens": estimate.estimated_prompt_tokens,
            "estimated_completion_tokens_upper_bound": (
                estimate.estimated_completion_tokens_upper_bound
            ),
            "estimated_total_tokens_upper_bound": (
                estimate.estimated_total_tokens_upper_bound
            ),
        }
        await self._record(
            kind="estimate",
            model=model,
            thinking_enabled=thinking_enabled,
            max_output_tokens=max_output_tokens,
            increments=increments,
        )

    async def record_actual(
        self,
        model: str,
        thinking_enabled: bool,
        max_output_tokens: int,
        result: UpdateDetectionResult,
    ) -> None:
        """累计一次 DeepSeek 实际调用结果。"""
        increments = {
            "request_attempt_count": 1,
            "api_success_count": int(result.api_success),
            "api_error_count": int(not result.api_success),
            "decision_yes_count": int(result.decision == "YES"),
            "decision_no_count": int(result.decision == "NO"),
            "invalid_decision_count": int(
                result.api_success and result.decision is None
            ),
            "truncated_count": int(result.truncated),
            "usage_missing_count": int(result.api_success and result.usage_missing),
            "prompt_tokens": result.prompt_tokens or 0,
            "completion_tokens": result.completion_tokens or 0,
            "total_tokens": result.total_tokens or 0,
        }
        await self._record(
            kind="actual",
            model=model,
            thinking_enabled=thinking_enabled,
            max_output_tokens=max_output_tokens,
            increments=increments,
        )

    async def _record(
        self,
        kind: str,
        model: str,
        thinking_enabled: bool,
        max_output_tokens: int,
        increments: dict[str, int],
    ) -> None:
        """在一个事务管道中写入元数据、计数和固定过期时间。"""
        now = datetime.now(timezone.utc)
        date_text = now.strftime("%Y%m%d")
        key = f"{self.KEY_PREFIX}:{kind}:{model}:{date_text}"
        expire_at = datetime.combine(
            now.date() + timedelta(days=self.RETENTION_DAYS + 1),
            time.min,
            tzinfo=timezone.utc,
        )
        timestamp = int(now.timestamp())

        try:
            async with self._redis.pipeline(transaction=True) as pipeline:
                pipeline.hsetnx(key, "first_recorded_at", timestamp)
                pipeline.hset(
                    key,
                    mapping={
                        "kind": kind,
                        "model": model,
                        "date": date_text,
                        "thinking_enabled": int(thinking_enabled),
                        "max_output_tokens": max_output_tokens,
                        "last_recorded_at": timestamp,
                    },
                )
                for field, amount in increments.items():
                    pipeline.hincrby(key, field, amount)
                pipeline.expireat(key, int(expire_at.timestamp()))
                await pipeline.execute()
        except Exception:
            logger.warning("写入更新检测 Token 统计失败", exc_info=True)
