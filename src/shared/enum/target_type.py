from enum import IntEnum


class TargetType(IntEnum):
    """Banner 目标类型"""

    THREAD = 1  # 论坛帖子
    CHANNEL = 2  # 频道
