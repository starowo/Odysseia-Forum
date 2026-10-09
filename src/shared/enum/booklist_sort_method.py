"""书单帖子排序方式枚举"""

from enum import Enum


class BooklistSortMethod(str, Enum):
    """书单帖子排序方式"""

    HOT = "hot"
    """热门排序（Reddit Hot 算法）"""

    CREATED_AT = "created_at"
    """发帖时间"""

    REACTION_COUNT = "reaction_count"
    """点赞数"""

    REPLY_COUNT = "reply_count"
    """回复数"""

    COLLECTION_COUNT = "collection_count"
    """收藏数"""

    LAST_ACTIVE_AT = "last_active_at"
    """最后发言时间"""

    JOIN_TIME = "join_time"
    """加入书单时间（BooklistItem.created_at）"""

    DISPLAY_ORDER = "display_order"
    """作者自定义排序"""
