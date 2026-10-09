"""删除Banner轮播/等待列表结果DTO"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DeleteBannerResult:
    """删除轮播或等待列表中Banner的操作结果"""

    success: bool
    message: str
    deleted_from: Optional[str] = None  # "carousel" 或 "waitlist"
    thread_id: Optional[int] = None
    banner_title: Optional[str] = None
    scope_label: Optional[str] = None  # "全频道" 或频道名称
    promoted_from_waitlist: bool = False  # 是否从等待列表晋升了替补
