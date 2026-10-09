"""书单发布状态枚举"""

from enum import IntEnum


class BooklistPublishStatus(IntEnum):
    """书单发布状态"""

    NONE = 0
    """未发布"""

    PENDING = 1
    """已提交，等待 friend 异步处理"""

    SUCCESS = 2
    """已成功发布"""

    FAILED = 3
    """发布失败"""
