from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class ThreadFollow(SQLModel, table=True):
    """用户关注帖子的关联表"""

    __tablename__ = "thread_follow"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="用户Discord ID")
    thread_id: int = Field(index=True, description="帖子Discord ID")
    followed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="关注时间"
    )
    last_viewed_at: Optional[datetime] = Field(
        default=None, description="最后查看时间，用于计算未读更新"
    )

    class Config:
        # 用户和帖子的组合必须唯一
        table_args = {"sqlite_autoincrement": True}
