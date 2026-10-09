"""请求级限频触发详情。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitTriggerDetail:
    """单个限频来源的计数、上限和重置时间。"""

    current_count: int
    max_requests: int
    reset_after: int
