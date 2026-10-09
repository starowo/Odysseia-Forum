from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class AuthorFollow(SQLModel, table=True):
    """存储用户对作者的关注关系。"""

    __tablename__ = "author_follow"  # type: ignore
    __table_args__ = (
        UniqueConstraint("user_id", "author_id", name="uk_author_follow_user_author"),
        CheckConstraint("user_id <> author_id", name="ck_author_follow_not_self"),
        Index(
            "ix_author_follow_author_active_user",
            "author_id",
            "active_flag",
            "user_id",
        ),
        Index(
            "ix_author_follow_user_active_followed",
            "user_id",
            "active_flag",
            "followed_at",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="关注者 Discord ID",
    )
    author_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="被关注作者 Discord ID",
    )
    followed_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
        description="最近一次关注时间",
    )
    active_flag: bool = Field(
        default=True,
        nullable=False,
        description="是否仍在关注",
    )
