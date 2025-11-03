from typing import List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship, BigInteger, Column, JSON

from .thread_tag_link import ThreadTagLink

if TYPE_CHECKING:
    from .tag import Tag
    from .tag_vote import TagVote
    from .author import Author


class Thread(SQLModel, table=True):
    """帖子模型。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True)
    thread_id: int = Field(index=True, unique=True)
    title: str
    author_id: int = Field(index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    last_active_at: Optional[datetime] = Field(default=None, index=True)
    reaction_count: int = Field(default=0, index=True)
    reply_count: int = Field(default=0, index=True)
    first_message_excerpt: Optional[str] = Field(default=None)
    thumbnail_urls: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    # 帖子更新相关字段
    latest_update_at: Optional[datetime] = Field(
        default=None, index=True, description="最新更新时间（贴主发布更新时刷新）"
    )
    latest_update_link: Optional[str] = Field(
        default=None, description="最新版消息链接"
    )

    # 帖子是否在搜索中显示
    show_flag: bool = Field(
        default=True,
        index=True,
        nullable=False,
        description="帖子是否应出现在搜索结果中",
    )

    # 审计用字段
    # 大于 0 则搜索不到，大于 5 则删除
    not_found_count: int = Field(
        default=0,
        index=True,
        description="审计拉取帖子数据 NotFound 时 +1, 拉取成功时归零",
    )

    # UCB1算法相关字段
    display_count: int = Field(
        default=0,
        sa_column=Column(BigInteger, index=True),
        description="在搜索结果中的展示次数",
    )

    tags: List["Tag"] = Relationship(back_populates="threads", link_model=ThreadTagLink)
    votes: List["TagVote"] = Relationship(back_populates="thread")

    # 作者关系
    author: Optional["Author"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Thread.author_id == Author.id",
            "foreign_keys": "[Thread.author_id]",
            "uselist": False,
            "lazy": "joined",
        }
    )
