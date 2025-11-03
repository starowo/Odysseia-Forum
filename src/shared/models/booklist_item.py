from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, UniqueConstraint


class BooklistItem(SQLModel, table=True):
    """书单内容关联表 (书单 <-> 帖子)"""

    __tablename__ = "booklist_item"  # type: ignore

    # 联合唯一索引：防止同一个帖子在同一个书单里出现两次
    __table_args__ = (
        UniqueConstraint("booklist_id", "thread_id", name="uq_booklist_thread"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    booklist_id: int = Field(index=True, description="所属书单ID")
    thread_id: int = Field(index=True, description="关联的帖子ID")

    # 排序权重，数字越小越靠前，或者按加入时间排
    display_order: int = Field(default=0, index=True)

    # 推荐语/备注 (用户在这个书单里对这个帖子的特殊评价)
    comment: Optional[str] = Field(default=None, description="书单主对该帖子的推荐语")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="加入书单的时间"
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        description="最后更新时间",
    )
