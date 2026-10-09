"""频率限制默认值"""

from enum import IntEnum


class RateLimitDefaults(IntEnum):
    """搜索和全局限流默认配置"""

    SEARCH_MAX_REQUESTS = 60
    """搜索接口每分钟最大请求数"""

    SIMILAR_MAX_REQUESTS = 60
    """相似推荐接口每分钟最大请求数"""

    GLOBAL_MAX_REQUESTS = 300
    """全局限流每分钟最大请求数（所有 /v1/* 接口）"""

    WINDOW_SECONDS = 60
    """限流窗口时长（秒）"""

    WATCH_TTL_SECONDS = 900
    """watch 标记有效期（秒），15 分钟"""

    DAILY_WATCH_THRESHOLD = 1500
    """单个服务器本地自然日触发 watch 的请求阈值"""

    LOG_BODY_MAX_CHARS = 1024
    """Watch 日志记录的请求体最大字符数"""
