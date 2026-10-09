from enum import Enum, IntEnum


class SearchConfigDefaults(float, Enum):
    """搜索配置默认值"""

    UCB1_EXPLORATION_FACTOR = 1.414  # sqrt(2)
    STRENGTH_WEIGHT = 5.0
    REDDIT_HOT_TIME_DECAY = 900_000.0  # 约 10.4 天衰减 1 分（原 450000 的 2 倍）


class SearchConfigDefaultsInt(IntEnum):
    """搜索配置默认值"""

    MAIN_GUILD_ID = 1134557553011998840  # 类脑服务器


class SearchConfigType(IntEnum):
    """搜索配置类型枚举"""

    TOTAL_DISPLAY_COUNT = 1  # 总展示次数 (N)
    UCB1_EXPLORATION_FACTOR = 2  # UCB1 探索因子 (C)
    STRENGTH_WEIGHT = 3  # 实力分权重 (W)
    NOTIFY_ON_MUTEX_CONFLICT = 4  # 互斥标签冲突通知开关
    MAIN_GUILD_ID = 5  # 主服务器 ID
    REDDIT_HOT_TIME_DECAY = 6  # Reddit Hot 时间衰减常量（秒）
