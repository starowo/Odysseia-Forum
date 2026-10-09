from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Index, event, func, inspect, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlmodel import Column, Field, SQLModel

from shared.text_utils import build_search_vector_text
from shared.time_utils import utc_now


class Booklist(SQLModel, table=True):
    """书单元数据"""

    __tablename__ = "booklist"  # type: ignore

    __table_args__ = (
        Index(
            "ix_booklist_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    """主键ID"""

    owner_id: int = Field(
        sa_column=Column(BigInteger, index=True),
        description="创建该书单的用户Discord ID",
    )
    """创建该书单的用户 Discord ID"""

    title: str = Field(index=True, description="书单标题")
    """书单标题"""

    description: Optional[str] = Field(default=None, description="书单简介")
    """书单简介"""

    # 封面图，可以是书单内第一个帖子的图，也可以是自定义
    cover_image_url: Optional[str] = Field(default=None, description="书单封面")
    """书单封面"""

    # 状态字段
    is_public: bool = Field(default=True, index=True, description="是否公开")
    """是否公开"""

    is_anonymous: bool = Field(default=False, index=True, description="是否匿名")
    """是否匿名"""

    is_default: bool = Field(
        default=False, index=True, description="是否为用户的默认书单"
    )
    """是否为用户的默认书单"""

    is_tournament: bool = Field(default=False, index=True, description="是否为赛事书单")
    """是否为赛事书单"""

    tournament_channel_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, index=True, unique=True),
        description="赛事关联的 Discord 频道ID",
    )
    """赛事关联的 Discord 频道ID"""

    publish_status: int = Field(
        default=0, index=True, description="发布状态: 0-未发布 1-待处理 2-成功 3-失败"
    )
    """发布状态: 0-未发布 1-待处理 2-成功 3-失败"""

    default_sort_method: str = Field(
        default="join_time",
        description="默认排序方式: hot, created_at, reaction_count, reply_count, collection_count, last_active_at, join_time, display_order",
    )
    """默认排序方式"""

    default_sort_order: str = Field(
        default="desc", description="默认排序顺序: asc, desc"
    )
    """默认排序顺序"""

    # 统计数据
    item_count: int = Field(default=0, description="书单内帖子数量")
    """书单内帖子数量"""

    view_count: int = Field(default=0, description="被浏览次数")
    """被浏览次数"""

    collection_count: int = Field(default=0, description="被收藏次数")
    """被收藏次数"""

    # Discord 展示位置
    display_thread_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="展示帖子的ID",
    )
    """展示帖子的 Discord ID"""

    display_channel_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="展示频道的ID",
    )
    """展示频道的 Discord ID"""

    display_guild_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="展示服务器的ID",
    )
    """展示服务器的 Discord ID"""

    created_at: datetime = Field(default_factory=utc_now, description="创建时间")
    """创建时间"""

    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": utc_now},
        description="最后更新时间",
    )
    """最后更新时间"""

    search_vector: Optional[str] = Field(
        default=None,
        sa_column=Column(TSVECTOR, nullable=True),
        description="预计算的 PostgreSQL 全文搜索向量（rjieba 分词 + to_tsvector('simple')）",
    )
    """全文搜索向量"""


# ── search_vector 自动维护 ────────────────────────────


@event.listens_for(Booklist, "before_insert")
def _on_booklist_before_insert(mapper, connection, target: Booklist):
    """INSERT 前自动填充 search_vector。"""
    tokens_text = build_search_vector_text(target.title, target.description)
    target.search_vector = (  # type: ignore[assignment]
        func.to_tsvector("simple", tokens_text) if tokens_text else None
    )


@event.listens_for(Booklist, "before_update")
def _on_booklist_before_update(mapper, connection, target: Booklist):
    """仅当 title 或 description 变化时重新计算 search_vector。"""
    insp = inspect(target)
    assert insp is not None, f"Expected ORM-mapped instance, got {type(target)}"
    title_changed = insp.attrs.title.history.has_changes()
    desc_changed = insp.attrs.description.history.has_changes()
    if not title_changed and not desc_changed:
        return
    tokens_text = build_search_vector_text(target.title, target.description)
    target.search_vector = (  # type: ignore[assignment]
        func.to_tsvector("simple", tokens_text) if tokens_text else None
    )


# ── table-level storage params (fillfactor=90) ──────────


@event.listens_for(Booklist.__table__, "after_create")  # type: ignore[attr-defined]
def _on_booklist_after_create(target, connection, **kw):  # type: ignore[no-redef]
    if connection.dialect.name == "postgresql":
        connection.execute(text("ALTER TABLE booklist SET (fillfactor = 90)"))
