from datetime import datetime

from pydantic import BaseModel, Field


class ThreadShareQueryDTO(BaseModel):
    """承载帖子 Repository 返回的脱离 Session 的分享数据。"""

    thread_id: int = Field(description="Discord 帖子 ID，仅供内部刷新与缓存校验")
    title: str
    description: str | None = None
    thumbnail_urls: list[str] = Field(default_factory=list)
    author_name: str | None = None
    author_avatar_url: str | None = None
    reaction_count: int = 0
    reply_count: int = 0
    collection_count: int = 0
    created_at: datetime
    updated_at: datetime
