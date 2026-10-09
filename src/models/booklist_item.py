from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlmodel import Column, Field, SQLModel, UniqueConstraint

from shared.time_utils import utc_now


class BooklistItem(SQLModel, table=True):
    """书单内容关联表 (书单 <-> 帖子)"""

    __tablename__ = "booklist_item"  # type: ignore

    # 联合唯一索引：防止同一个帖子在同一个书单里出现两次
    __table_args__ = (
        UniqueConstraint("booklist_id", "thread_id", name="uq_booklist_thread"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    """主键ID"""

    owner_id: int = Field(
        default=0,
        sa_column=Column(BigInteger, index=True),
        description="所属用户的ID",
    )
    """所属用户的ID"""

    booklist_id: int = Field(
        sa_column=Column(BigInteger, index=True), description="所属书单ID"
    )
    """所属书单ID"""

    thread_id: int = Field(
        sa_column=Column(BigInteger, index=True), description="关联的帖子ID"
    )
    """关联的帖子ID"""

    display_order: int = Field(default=0, index=True)
    """（可选的）排序数据，用于控制展示顺序"""

    # 推荐语/备注 (用户在这个书单里对这个帖子的特殊评价)
    comment: Optional[str] = Field(default=None, description="书单主对该帖子的备注")
    """书单主对该帖子的备注"""

    tournament_participated_at: Optional[datetime] = Field(
        default=None, description="参赛时间（赛事专用）"
    )
    """参赛时间（赛事专用）"""

    display_message_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="展示消息的ID",
    )
    """展示消息的 Discord ID"""

    created_at: datetime = Field(default_factory=utc_now, description="加入书单的时间")
    """加入书单的时间"""

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": utc_now},
        description="最后更新时间",
    )
    """最后更新时间"""
