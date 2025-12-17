from typing import Optional

from sqlmodel import Field, SQLModel


class ThreadTagLink(SQLModel, table=True):
    """帖子和标签的多对多关联表模型。"""

    thread_id: Optional[int] = Field(
        default=None, foreign_key="thread.id", primary_key=True
    )
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
    upvotes: int = Field(default=0)
    downvotes: int = Field(default=0)
