from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class BannerWaitlist(SQLModel, table=True):
    """Banner等待列表"""

    __tablename__ = "banner_waitlist"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(index=True, description="帖子ID")
    channel_id: Optional[int] = Field(
        default=None, index=True, description="频道ID，NULL表示全频道"
    )
    cover_image_url: str = Field(description="封面图链接")
    title: str = Field(description="帖子标题")

    queued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="加入队列时间",
    )
    position: int = Field(default=0, index=True, description="队列位置")
