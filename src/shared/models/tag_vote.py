from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint

if TYPE_CHECKING:
    from .tag import Tag
    from .thread import Thread


class TagVote(SQLModel, table=True):
    """标签投票模型，记录用户对特定帖子中特定标签的评价。"""

    __tablename__ = "tag_vote"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "tag_id", "thread_id", name="uq_user_tag_thread_vote"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    tag_id: int = Field(index=True, foreign_key="tag.id")
    thread_id: int = Field(index=True, foreign_key="thread.id")
    vote: int  # 1 代表赞成, -1 代表反对

    # 关系定义，用于 ORM 查询，不产生外键约束
    tag: "Tag" = Relationship(back_populates="votes")
    thread: "Thread" = Relationship(back_populates="votes")
