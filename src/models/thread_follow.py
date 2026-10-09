from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Index, UniqueConstraint
from sqlmodel import Column, Field, SQLModel

from shared.time_utils import utc_now


class ThreadFollow(SQLModel, table=True):
    """用户关注帖子的关联表"""

    __tablename__ = "thread_follow"  # type: ignore
    __table_args__ = (
        UniqueConstraint("user_id", "thread_id", name="uk_thread_follow_user_thread"),
        Index(
            "ix_thread_follow_thread_active_user",
            "thread_id",
            "active_flag",
            "user_id",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(BigInteger, index=True), description="用户Discord ID"
    )
    thread_id: int = Field(
        sa_column=Column(BigInteger, index=True), description="帖子Discord ID"
    )
    followed_at: datetime = Field(default_factory=utc_now, description="关注时间")
    last_viewed_at: Optional[datetime] = Field(
        default=None, description="最后查看时间，用于计算未读更新"
    )
    active_flag: bool = Field(
        default=True, description="是否为当前关注（False表示过去关注）"
    )
