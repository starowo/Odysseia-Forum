from datetime import datetime

from sqlalchemy import BigInteger, Column, JSON, Index
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class OperationLog(SQLModel, table=True):
    """保存管理与治理操作的审计快照，支持扩展其他操作类型。"""

    __tablename__ = "operation_log"
    __table_args__ = (
        Index("ix_operation_log_target_history", "target_type", "target_id", "id"),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="操作日志的内部主键",
    )
    """操作日志的内部主键"""

    type: str = Field(
        index=True,
        description="操作类型，例如 tag.bind、tag.unbind、tag.vote、tag.review 或 tag.pool.*；预留用于扩展",
    )
    """操作类型，例如 tag.bind、tag.unbind、tag.vote、tag.review 或 tag.pool.*；预留用于扩展"""

    actor_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="操作者的 Discord 用户 ID；系统操作可为空或为 0",
    )
    """操作者的 Discord 用户 ID；系统操作可为空或为 0"""

    target_type: str = Field(
        index=True,
        description="操作目标类型：thread 为帖子，booklist 为书单，tag 为标签实体",
    )
    """操作目标类型：thread 为帖子，booklist 为书单，tag 为标签实体"""

    target_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, index=True),
        description="操作目标 ID：内部帖子 ID、内部书单 ID 或内部标签 ID，由 target_type 决定",
    )
    """操作目标 ID：内部帖子 ID、内部书单 ID 或内部标签 ID，由 target_type 决定"""

    tag_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger),
        description="操作关联的内部标签 ID；非标签类操作可为空，标签删除后仍保留此审计引用",
    )
    """操作关联的内部标签 ID；非标签类操作可为空，标签删除后仍保留此审计引用"""

    detail: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
        description="操作详情快照，按类型保存标签名称、分类、变更前后值、轮次、票数或原因",
    )
    """操作详情快照，按类型保存标签名称、分类、变更前后值、轮次、票数或原因"""

    created_at: datetime = Field(
        default_factory=utc_now, description="操作记录创建时间（UTC）"
    )
    """操作记录创建时间（UTC）"""
