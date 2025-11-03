from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from ..search.author import AuthorDetail


class BooklistItemDetail(BaseModel):
    """书单项目详情，包含帖子信息"""

    booklist_item_id: int = Field(description="书单项ID")
    thread_id: int = Field(description="帖子ID")
    channel_id: int = Field(description="频道ID")
    title: str = Field(description="帖子标题")
    author: AuthorDetail = Field(description="帖子作者信息")
    created_at: datetime = Field(description="帖子创建时间")
    reaction_count: int = Field(description="帖子点赞数")
    reply_count: int = Field(description="帖子回复数")
    thumbnail_urls: List[str] = Field(description="帖子首楼图片URL列表")
    comment: Optional[str] = Field(None, description="书单主对该帖子的推荐语")
    display_order: int = Field(description="排序权重")
    added_at: datetime = Field(description="加入书单的时间")
    collected_flag: bool = Field(False, description="当前用户是否收藏了该帖子")

    @field_serializer("thread_id", "channel_id")
    def serialize_ids(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)

    class Config:
        from_attributes = True
