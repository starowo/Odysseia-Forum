"""Booklist 数据传输对象 — 安全用于 session 外。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BooklistDTO(BaseModel):
    """Booklist 的轻量 DTO。仅包含标量字段，不包含关系。"""

    id: Optional[int] = Field(default=None, description="主键 ID")
    owner_id: int = Field(description="创建该书单的用户 Discord ID")
    title: str = Field(description="书单标题")
    description: Optional[str] = Field(default=None, description="书单简介")
    cover_image_url: Optional[str] = Field(default=None, description="书单封面")
    is_public: bool = Field(default=True, description="是否公开")
    is_anonymous: bool = Field(default=False, description="是否匿名")
    is_default: bool = Field(default=False, description="是否为用户的默认书单")
    is_tournament: bool = Field(default=False, description="是否为赛事书单")
    tournament_channel_id: Optional[int] = Field(
        default=None, description="赛事关联的 Discord 频道 ID"
    )
    default_sort_method: str = Field(default="join_time", description="默认排序方式")
    default_sort_order: str = Field(default="desc", description="默认排序顺序")
    item_count: int = Field(default=0, description="书单内帖子数量")
    view_count: int = Field(default=0, description="被浏览次数")
    collection_count: int = Field(default=0, description="被收藏次数")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")

    @staticmethod
    def from_orm(booklist) -> "BooklistDTO":
        """从 Booklist ORM 对象构建 BooklistDTO（须在 session 内调用）。"""
        return BooklistDTO(
            id=booklist.id,
            owner_id=booklist.owner_id,
            title=booklist.title,
            description=booklist.description,
            cover_image_url=booklist.cover_image_url,
            is_public=booklist.is_public,
            is_anonymous=booklist.is_anonymous,
            is_default=booklist.is_default,
            is_tournament=booklist.is_tournament,
            tournament_channel_id=booklist.tournament_channel_id,
            default_sort_method=booklist.default_sort_method,
            default_sort_order=booklist.default_sort_order,
            item_count=booklist.item_count,
            view_count=booklist.view_count,
            collection_count=booklist.collection_count,
            created_at=booklist.created_at,
            updated_at=booklist.updated_at,
        )
