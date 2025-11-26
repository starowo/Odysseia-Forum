from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from ..base import PaginatedResponse
from .author import AuthorDetail
from ..banner import BannerItem


class ThreadDetail(BaseModel):
    """
    API 响应中单个帖子的详细信息模型
    """

    thread_id: int = Field(description="帖子的 Discord ID")
    channel_id: int = Field(description="帖子所在频道的 Discord ID")
    title: str = Field(description="帖子标题")
    author: Optional[AuthorDetail] = Field(description="帖子作者的详细信息")
    created_at: datetime = Field(description="帖子创建时间")
    last_active_at: Optional[datetime] = Field(description="帖子最后活跃时间")
    reaction_count: int = Field(description="帖子点赞数")
    reply_count: int = Field(description="帖子回复数")
    display_count: int = Field(description="在搜索结果中的展示次数")
    first_message_excerpt: Optional[str] = Field(description="帖子首条消息摘要")
    thumbnail_urls: List[str] = Field(
        default_factory=list,
        description="帖子首楼图片 URL 列表（按出现顺序）"
    )
    tags: List[str] = Field(description="帖子关联的标签列表")

    @field_serializer('thread_id', 'channel_id')
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)

    class Config:
        from_attributes = True


class SearchResponse(PaginatedResponse[ThreadDetail]):
    """搜索接口的最终响应体"""

    available_tags: List[str] = Field(
        default_factory=list,
        description="当搜索单个频道时返回该频道的可用标签列表，全频道搜索时返回空列表"
    )
    banner_carousel: List[BannerItem] = Field(
        default_factory=list,
        description="Banner轮播列表，包含当前频道+全频道的banner（最多8个）"
    )
    unread_count: int = Field(
        default=0,
        description="当前用户关注列表的未读更新数量"
    )
