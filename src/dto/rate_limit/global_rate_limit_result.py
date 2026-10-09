"""全局频率限制检查结果。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GlobalRateLimitResult:
    """全局分钟计数、每日计数与 Watch 状态。"""

    allowed: bool
    minute_count: int
    minute_remaining: int
    reset_after: int
    daily_count: int
    watched: bool
    daily_watch_active: bool

    @classmethod
    def fail_open(cls, max_requests: int) -> "GlobalRateLimitResult":
        """构造 Redis 异常时的降级放行结果。"""
        return cls(
            allowed=True,
            minute_count=0,
            minute_remaining=max_requests,
            reset_after=0,
            daily_count=0,
            watched=False,
            daily_watch_active=False,
        )
