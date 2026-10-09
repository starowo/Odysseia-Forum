from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Index,
    String,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class ThreadUpdate(SQLModel, table=True):
    """存储作品正式发布的更新历史。"""

    __tablename__ = "thread_update"  # type: ignore
    __table_args__ = (
        UniqueConstraint("message_id", name="uk_thread_update_message"),
        UniqueConstraint(
            "overview_message_id",
            name="uk_thread_update_overview_message",
        ),
        CheckConstraint(
            "char_length(btrim(description)) BETWEEN 1 AND 500",
            name="ck_thread_update_description_length",
        ),
        CheckConstraint(
            "version IS NULL OR char_length(btrim(version)) BETWEEN 1 AND 50",
            name="ck_thread_update_version_length",
        ),
        Index(
            "ix_thread_update_thread_published",
            "thread_id",
            "published_at",
            "id",
        ),
        Index(
            "ix_thread_update_publisher_published",
            "publisher_id",
            "published_at",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="作品 Discord Thread ID",
    )
    message_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
        description="来源 Discord 消息 ID",
    )
    publisher_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="发布者 Discord ID",
    )
    description: str = Field(
        sa_column=Column(String(500), nullable=False),
        description="更新描述",
    )
    version: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50), nullable=True),
        description="可选版本号",
    )
    source_message_at: datetime = Field(
        nullable=False,
        description="来源消息发布时间",
    )
    published_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
        description="正式发布时间",
    )
    overview_message_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
        description="自动发布概览消息 ID",
    )
