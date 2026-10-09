from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class Notification(SQLModel, table=True):
    """存储面向单个接收者的动态通知。"""

    __tablename__ = "notification"  # type: ignore
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_type",
            "event_source_id",
            name="uk_notification_user_event_source",
        ),
        CheckConstraint(
            "event_type IN ('thread_update', 'author_new_thread', 'tag_review')",
            name="ck_notification_event_type",
        ),
        Index(
            "ix_notification_user_created",
            "user_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_notification_event_source",
            "event_type",
            "event_source_id",
        ),
        Index(
            "ix_notification_unread_user",
            "user_id",
            "created_at",
            postgresql_where=text("read_at IS NULL"),
        ),
        Index(
            "ix_notification_unread_user_thread",
            "user_id",
            "thread_id",
            postgresql_where=text("read_at IS NULL"),
        ),
    )

    id: Optional[int] = Field(
        default=None, primary_key=True, description="通知记录的内部主键"
    )
    """通知记录的内部主键"""

    user_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="通知接收者的 Discord 用户 ID",
    )
    """通知接收者的 Discord 用户 ID"""

    event_type: str = Field(
        sa_column=Column(String(32), nullable=False),
        description="通知事件类型：thread_update 为作品更新，author_new_thread 为作者新作，tag_review 为标签审核",
    )
    """通知事件类型：thread_update 为作品更新，author_new_thread 为作者新作，tag_review 为标签审核"""

    event_source_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="事件来源 ID：作品更新记录 ID、作者新作的 Discord 帖子 ID 或标签申请 ID，与事件类型共同定位来源",
    )
    """事件来源 ID：作品更新记录 ID、作者新作的 Discord 帖子 ID 或标签申请 ID，与事件类型共同定位来源"""

    thread_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True),
        description="作品动态关联的 Discord 帖子 ID；标签审核通知通过 target_type 和 target_id 定位，此字段可为空",
    )
    """作品动态关联的 Discord 帖子 ID；标签审核通知通过 target_type 和 target_id 定位，此字段可为空"""

    target_type: str | None = Field(
        default=None,
        description="标签审核目标类型：thread 为帖子，booklist 为书单；作品动态通知为空",
    )
    """标签审核目标类型：thread 为帖子，booklist 为书单；作品动态通知为空"""

    target_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="标签审核目标 ID：Discord 帖子 ID 或内部书单 ID；作品动态通知为空",
    )
    """标签审核目标 ID：Discord 帖子 ID 或内部书单 ID；作品动态通知为空"""

    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
        description="通知创建时间（UTC）",
    )
    """通知创建时间（UTC）"""

    read_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="用户阅读时间（UTC）；为空表示未读",
    )
    """用户阅读时间（UTC）；为空表示未读"""
