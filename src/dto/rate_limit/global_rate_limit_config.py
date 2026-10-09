"""全局频率限制配置。"""

from dataclasses import dataclass
from typing import Any, Mapping

from shared.enum.rate_limit_defaults import RateLimitDefaults


@dataclass(frozen=True)
class GlobalRateLimitConfig:
    """全局分钟限流和每日 Watch 阈值配置。"""

    max_requests: int = int(RateLimitDefaults.GLOBAL_MAX_REQUESTS)
    window_seconds: int = int(RateLimitDefaults.WINDOW_SECONDS)
    daily_watch_threshold: int = int(RateLimitDefaults.DAILY_WATCH_THRESHOLD)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "GlobalRateLimitConfig":
        """从配置映射构建全局限频配置，无效值回退到默认值。"""
        values = raw or {}
        return cls(
            max_requests=cls._positive_int(
                values.get("max_requests"), RateLimitDefaults.GLOBAL_MAX_REQUESTS
            ),
            daily_watch_threshold=cls._positive_int(
                values.get("daily_watch_threshold"),
                RateLimitDefaults.DAILY_WATCH_THRESHOLD,
            ),
        )

    @staticmethod
    def _positive_int(value: Any, default: int) -> int:
        """将配置值转换为正整数。"""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return int(default)
        return parsed if parsed > 0 else int(default)
