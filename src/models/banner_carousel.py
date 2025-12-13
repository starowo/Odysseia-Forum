from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class BannerCarousel(SQLModel, table=True):
    """Banner轮播列表"""

    __tablename__ = "banner_carousel"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(index=True, description="帖子ID")
    channel_id: Optional[int] = Field(
        default=None, index=True, description="频道ID，NULL表示全频道"
    )
    cover_image_url: str = Field(description="封面图链接")
    title: str = Field(description="帖子标题")

    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        description="开始展示时间",
    )
    end_time: datetime = Field(index=True, description="结束展示时间（3天后）")
    position: int = Field(default=0, index=True, description="展示位置顺序")
