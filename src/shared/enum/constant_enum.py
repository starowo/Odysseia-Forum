from enum import IntEnum


class ConstantEnum(IntEnum):
    """通用常量"""

    DEFAULT_SURGE_DAYS = 30
    """默认统计天数"""

    MAX_SURGE_DAYS = 90
    """最大统计天数"""

    TREND_CACHE_EXPIRE_SECONDS = 600
    """趋势缓存过期时间（秒）—— 10 分钟"""

    CHANNELS_CACHE_EXPIRE_SECONDS = 1800
    """频道元数据缓存过期时间（秒）—— 30 分钟"""

    STATISTICS_THRESHOLD_DAYS = 15
    """只有最近 15 天内创建的帖子才计入趋势统计"""

    AUTH_CACHE_TTL = 86400
    """Discord 成员信息缓存 TTL（秒）—— 1 天"""

    PREF_CACHE_TTL = 7200
    """用户搜索偏好缓存 TTL（秒）—— 2 小时"""
