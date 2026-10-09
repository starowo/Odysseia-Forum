from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BannerStatusItem:
    """用于状态展示的轮播快照。"""

    target_id: int
    """Banner 指向的帖子或频道 ID，不是展示范围的频道 ID"""

    target_type: int
    """目标类型，对应 TargetType：1 为帖子，2 为频道"""

    title: str
    """目标标题的完整快照，由视图负责截断展示"""

    end_time: datetime
    """轮播结束时间，使用不带时区信息的 UTC 时间"""
