from datetime import datetime
from typing import Optional

from sqlmodel import BigInteger, Column, Field, SQLModel, UniqueConstraint

from shared.time_utils import utc_now

from shared.enum import CollectionType


class UserCollection(SQLModel, table=True):
    """存储用户收藏的内容"""

    __tablename__ = "user_collection"  # type: ignore

    __table_args__ = (
        UniqueConstraint(
            "user_id", "target_type", "target_id", name="uk_user_collection_target"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(
        sa_column=Column(BigInteger, index=True), description="收藏用户的 Discord ID"
    )

    target_type: int = Field(
        default=CollectionType.THREAD.value,
        index=True,
        description="收藏目标的类型 : 1=帖子(已废弃使用), 2=书单, 默认为 1 ",
    )

    target_id: int = Field(
        sa_column=Column(BigInteger, index=True),
        description="目标对象的ID (Thread 的 discord ID 或 Booklist ID)",
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
        description="收藏时间 (UTC)",
    )
    note: Optional[str] = Field(default=None, description="用户为收藏添加的备注")
