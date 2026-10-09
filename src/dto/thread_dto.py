"""Thread 数据传输对象 — 安全用于 session 外。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from dto.tag_dto import TagDTO


class ThreadDTO(BaseModel):
    """Thread 的轻量 DTO。tags 存为 list[TagDTO]，author 存为 author_id:int。

    相比 ORM 对象剥离了 SQLAlchemy instrumentation、relationship backref、
    identity map 引用等内存开销。
    """

    id: Optional[int] = Field(default=None, description="数据库主键 ID")
    guild_id: int = Field(description="Discord 服务器 ID")
    channel_id: int = Field(description="帖子所在频道的 Discord ID")
    thread_id: int = Field(description="帖子的 Discord ID")
    title: str = Field(description="帖子标题")
    author_id: int = Field(description="帖子作者的 Discord ID")
    created_at: datetime = Field(description="帖子创建时间 (UTC)")
    last_active_at: Optional[datetime] = Field(
        default=None, description="帖子最后活跃时间 (UTC)"
    )
    reaction_count: int = Field(default=0, description="帖子获得的总反应数")
    reply_count: int = Field(default=0, description="帖子的回复数量")
    collection_count: int = Field(default=0, description="被收藏次数")
    display_count: int = Field(default=0, description="搜索结果展示次数")
    first_message_excerpt: Optional[str] = Field(
        default=None, description="帖子首条消息的文本摘要"
    )
    thumbnail_urls: list[str] = Field(
        default_factory=list, description="首楼图片链接列表"
    )
    tags: list[TagDTO] = Field(default_factory=list, description="关联的标签列表")
    latest_update_at: Optional[datetime] = Field(
        default=None, description="最新更新时间"
    )
    latest_update_link: Optional[str] = Field(
        default=None, description="最新更新消息链接"
    )
    latest_update_id: Optional[int] = Field(
        default=None, description="最新作品更新逻辑 ID"
    )

    @staticmethod
    def from_orm(thread) -> "ThreadDTO":
        """从 Thread ORM 对象构建 ThreadDTO（须在 session 内调用）。"""
        return ThreadDTO(
            id=thread.id,
            guild_id=thread.guild_id,
            channel_id=thread.channel_id,
            thread_id=thread.thread_id,
            title=thread.title,
            author_id=thread.author_id,
            created_at=thread.created_at,
            last_active_at=thread.last_active_at,
            reaction_count=thread.reaction_count,
            reply_count=thread.reply_count,
            collection_count=thread.collection_count,
            display_count=thread.display_count,
            first_message_excerpt=thread.first_message_excerpt,
            thumbnail_urls=thread.thumbnail_urls or [],
            tags=[TagDTO.from_orm(tag) for tag in (thread.tags or [])],
            latest_update_at=thread.latest_update_at,
            latest_update_link=thread.latest_update_link,
            latest_update_id=thread.latest_update_id,
        )
