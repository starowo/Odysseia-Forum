from dataclasses import dataclass

from banner.dto.banner_status_item import BannerStatusItem


@dataclass(frozen=True)
class BannerScopeStatus:
    """单个展示范围的轮播和等待数量快照。"""

    channel_id: int | None
    """展示范围的频道 ID，None 表示全频道"""

    capacity: int
    """该展示范围允许同时轮播的 Banner 数量上限"""

    waiting_count: int
    """已通过审核、正在等待轮播空位的数量，不含待审核申请"""

    items: list[BannerStatusItem]
    """当前未过期轮播，按队列位置和记录 ID 排序"""
