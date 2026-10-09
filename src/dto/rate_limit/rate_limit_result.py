"""频率限制检查结果。"""

from dataclasses import dataclass


@dataclass
class RateLimitResult:
    """频率限制检查结果"""

    allowed: bool
    current_count: int = 0
    remaining: int = 0
    reset_after: int = 0

    @classmethod
    def fail_open(cls) -> "RateLimitResult":
        """Redis 不可用时的降级结果：放行"""
        return cls(allowed=True, remaining=9999, reset_after=0)
