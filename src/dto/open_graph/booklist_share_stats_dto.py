from pydantic import BaseModel, Field


class BooklistShareStatsDTO(BaseModel):
    """描述书单分享卡片中的公开统计。"""

    item_count: int = Field(description="当前可见作品数")
    collection_count: int = Field(description="书单收藏数")
    view_count: int = Field(description="书单浏览数")
