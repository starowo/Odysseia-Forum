from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime


class BooklistDetail(BaseModel):
    """书单详情"""

    id: int = Field(description="书单ID")
    owner_id: int = Field(description="创建者用户ID")
    title: str = Field(description="书单标题")
    description: Optional[str] = Field(None, description="书单简介")
    cover_image_url: Optional[str] = Field(None, description="书单封面图URL")
    is_public: bool = Field(description="是否公开")
    display_type: int = Field(
        description="展示方式: 1=加入时间倒序, 2=作者自定义排序(display_order)"
    )
    item_count: int = Field(description="书单内帖子数量")
    collection_count: int = Field(description="被收藏次数")
    view_count: int = Field(description="被浏览次数")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")
    collected_flag: bool = Field(False, description="当前用户是否收藏了该书单")

    @field_serializer("owner_id")
    def serialize_owner_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)

    class Config:
        from_attributes = True
