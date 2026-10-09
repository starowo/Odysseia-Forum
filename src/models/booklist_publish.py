from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, UniqueConstraint
from sqlmodel import Column, Field, SQLModel

from shared.time_utils import utc_now


class BooklistPublish(SQLModel, table=True):
    """书单发布记录，关联书单与其发布到的 Discord 讨论帖"""

    __tablename__ = "booklist_publish"  # type: ignore

    __table_args__ = (
        UniqueConstraint("booklist_id", name="uq_booklist_publish_booklist"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    """主键ID"""

    booklist_id: int = Field(
        sa_column=Column(BigInteger, index=True, nullable=False),
        description="所属书单ID",
    )
    """所属书单ID"""

    guild_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="Discord 服务器 ID",
    )
    """Discord 服务器 ID"""

    thread_id: int = Field(
        sa_column=Column(BigInteger, index=True, nullable=False),
        description="Discord 讨论帖 ID",
    )
    """Discord 讨论帖 ID"""

    discord_user_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="发布者 Discord 用户 ID",
    )
    """发布者 Discord 用户 ID"""

    message_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
        description="书单发布 API 返回的 Discord 消息 ID",
    )
    """书单发布 API 返回的 Discord 消息 ID """

    message_url: Optional[str] = Field(
        default=None, description="书单发布 API 返回的消息 URL"
    )
    """书单发布 API 返回的消息 URL"""

    created_at: datetime = Field(default_factory=utc_now, description="创建时间")
    """创建时间"""

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": utc_now},
        description="最后更新时间",
    )
    """最后更新时间"""
