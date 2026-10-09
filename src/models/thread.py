from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Index, event, func, inspect, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlmodel import JSON, BigInteger, Column, Field, Relationship, SQLModel

from shared.text_utils import build_search_vector_text
from shared.time_utils import utc_now

if TYPE_CHECKING:
    from models import Author, Tag


class Thread(SQLModel, table=True):
    """帖子模型。"""

    __table_args__ = (
        Index("ix_thread_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    """数据库主键 ID"""

    guild_id: int = Field(
        default=0,
        sa_column=Column(BigInteger, index=True, nullable=False),
        description="帖子所属的 Discord 服务器 ID",
    )
    """帖子所属的 Discord 服务器 ID"""

    channel_id: int = Field(
        sa_column=Column(BigInteger, index=True),
        description="帖子所在频道的 Discord ID",
    )
    """帖子所在频道的 Discord ID"""

    thread_id: int = Field(
        sa_column=Column(BigInteger, index=True, unique=True),
        description="帖子的 Discord ID",
    )
    """帖子的 Discord ID"""

    title: str
    """帖子标题"""

    native_tag_revision: int = Field(
        default=0,
        description="原生标签集合每次变更时递增的修订号，参与标签编辑版本校验",
    )
    """原生标签变更修订号，用于识别同步导致的并发变更"""

    author_id: int = Field(
        sa_column=Column(BigInteger, index=True),
        description="帖子作者的 Discord ID",
    )

    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    """帖子创建时间 (UTC)"""

    last_active_at: Optional[datetime] = Field(default=None, index=True)
    """帖子最后活跃时间 (UTC)"""

    reaction_count: int = Field(default=0, index=True)
    """帖子获得的总反应数"""

    reply_count: int = Field(default=0, index=True)
    """帖子的回复数量"""

    first_message_excerpt: Optional[str] = Field(default=None)
    """帖子首条消息的文本摘要"""

    search_vector: Optional[str] = Field(
        default=None,
        sa_column=Column(TSVECTOR, nullable=True),
        description="预计算的 PostgreSQL 全文搜索向量（rjieba 分词 + to_tsvector('simple')），支持 <-> / <N> 邻近搜索",
    )
    """PostgreSQL 全文搜索向量"""

    thumbnail_urls: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    """帖子首楼提取的图片链接列表"""

    latest_update_at: Optional[datetime] = Field(
        default=None, index=True, description="最新更新时间（贴主发布更新时刷新）"
    )
    """最新更新时间（贴主发布更新时刷新）"""

    latest_update_link: Optional[str] = Field(
        default=None, description="最新版消息链接"
    )
    """最新版消息链接"""

    latest_update_id: Optional[int] = Field(
        default=None,
        index=True,
        description="最新 ThreadUpdate 的逻辑 ID",
    )
    """最新 ThreadUpdate 的逻辑 ID"""

    collection_count: int = Field(default=0, description="被收藏次数")
    """帖子被收藏的总次数"""

    show_flag: bool = Field(
        default=True,
        index=True,
        nullable=False,
        description="帖子是否应出现在搜索结果中",
    )
    """帖子是否在搜索结果中显示"""

    not_found_count: int = Field(
        default=0,
        index=True,
        description="审计拉取帖子数据 NotFound 时 +1, 拉取成功时归零",
    )
    """拉取失败次数，大于 0 则搜索不到，大于5则删除"""

    display_count: int = Field(
        default=0,
        sa_column=Column(BigInteger, index=True),
        description="在搜索结果中的展示次数",
    )
    """在搜索结果中的总展示次数"""

    tags: List["Tag"] = Relationship(
        sa_relationship_kwargs={
            "secondary": "tag_binding",
            "primaryjoin": "and_(Thread.id == foreign(TagBinding.target_id), TagBinding.target_type == 'thread', TagBinding.ended_at.is_(None))",
            "secondaryjoin": "and_(Tag.id == foreign(TagBinding.tag_id), Tag.deleted_at.is_(None))",
            "viewonly": True,
        },
    )
    """统一绑定中的全部有效标签，只读；写入由绑定仓储负责"""

    author: Optional["Author"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Thread.author_id == Author.id",
            "foreign_keys": "[Thread.author_id]",
            "uselist": False,
            "lazy": "select",
        }
    )
    """帖子作者的关系映射"""


# ── search_vector 自动维护 ────────────────────────────


@event.listens_for(Thread, "before_insert")
def _on_thread_before_insert(mapper, connection, target: Thread):
    """INSERT 前自动填充 search_vector。"""
    tokens_text = build_search_vector_text(target.title, target.first_message_excerpt)
    target.search_vector = (  # type: ignore[assignment]
        func.to_tsvector("simple", tokens_text) if tokens_text else None
    )


@event.listens_for(Thread, "before_update")
def _on_thread_before_update(mapper, connection, target: Thread):
    """仅当 title 或 first_message_excerpt 变化时重新计算 search_vector。"""
    insp = inspect(target)
    assert insp is not None, f"Expected ORM-mapped instance, got {type(target)}"
    title_changed = insp.attrs.title.history.has_changes()
    excerpt_changed = insp.attrs.first_message_excerpt.history.has_changes()
    if not title_changed and not excerpt_changed:
        return
    tokens_text = build_search_vector_text(target.title, target.first_message_excerpt)
    target.search_vector = (  # type: ignore[assignment]
        func.to_tsvector("simple", tokens_text) if tokens_text else None
    )


# ── table-level storage params (fillfactor=90) ──────────


@event.listens_for(Thread.__table__, "after_create")  # type: ignore[attr-defined]
def _on_thread_after_create(target, connection, **kw):  # type: ignore[no-redef]
    if connection.dialect.name == "postgresql":
        connection.execute(text("ALTER TABLE thread SET (fillfactor = 90)"))
