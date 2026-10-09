"""频率限制运行时配置（从 config.json 读取后实例化）。"""

from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """频率限制配置"""

    max_requests: int = 40
    window_seconds: int = 60
    key_prefix: str = "rate_limit"
