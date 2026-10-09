from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, Column, SmallInteger
from sqlmodel import Field, SQLModel

from shared.enum import TargetType
from shared.time_utils import utc_now


class BannerWaitlist(SQLModel, table=True):
    """Banner等待列表"""

    __tablename__ = "banner_waitlist"  # type: ignore
    __table_args__ = (
        CheckConstraint(
            "target_type <> 2 OR cover_image_url IS NOT NULL",
            name="ck_banner_waitlist_channel_cover",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(
        sa_column=Column(BigInteger, index=True), description="帖子ID"
    )
    channel_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, index=True),
        description="频道ID，NULL表示全频道",
    )
    cover_image_url: Optional[str] = Field(
        default=None,
        description="自定义封面图；帖子为空时动态使用首楼图",
    )
    title: str = Field(description="帖子标题")
    target_type: int = Field(
        default=TargetType.THREAD.value,
        sa_column=Column(SmallInteger, index=True, nullable=False),
        description="论坛帖子 / 频道",
    )

    queued_at: datetime = Field(
        default_factory=utc_now,
        index=True,
        description="加入队列时间",
    )
    position: int = Field(default=0, index=True, description="队列位置")
