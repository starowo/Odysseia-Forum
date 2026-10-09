from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Column, Index, text
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class TagBinding(SQLModel, table=True):
    """保存原生或本地标签的一轮绑定及汇总票数，解绑后保留历史。"""

    __tablename__ = "tag_binding"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="本轮挂标记录的内部主键；重新挂标会创建新的轮次 ID",
    )
    """本轮挂标记录的内部主键；重新挂标会创建新的轮次 ID"""

    target_type: str = Field(
        index=True, description="绑定目标类型：thread 为帖子，booklist 为书单"
    )
    """绑定目标类型：thread 为帖子，booklist 为书单"""

    target_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, index=True),
        description="绑定目标 ID：帖子使用内部帖子 ID，书单使用内部书单 ID",
    )
    """绑定目标 ID：帖子使用内部帖子 ID，书单使用内部书单 ID"""

    tag_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, index=True),
        description="绑定的标签内部 ID",
    )
    """绑定的标签内部 ID"""

    binding_source: str = Field(
        default="local",
        description="绑定来源：discord_sync 为只读同步，local 为项目内添加",
    )
    """绑定来源决定治理权限，与标签实体来源独立"""

    discord_source_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, index=True),
        description="DC 同步绑定的来源记录 ID；本地绑定为空",
    )
    """同步绑定对应唯一来源，历史轮次保留来源引用"""

    actor_id: int | None = Field(
        sa_column=Column(BigInteger, nullable=True),
        default=None,
        description="执行挂标的 Discord 用户 ID；自动超时挂标时为 0",
    )
    """执行挂标的 Discord 用户 ID；自动超时挂标时为 0"""

    created_at: datetime = Field(
        default_factory=utc_now, description="本轮挂标创建时间（UTC）"
    )
    """本轮挂标创建时间（UTC）"""

    ended_at: datetime | None = Field(
        default=None, description="本轮解绑时间（UTC）；为空表示当前仍生效"
    )
    """本轮解绑时间（UTC）；为空表示当前仍生效"""

    end_reason: str | None = Field(
        default=None,
        description="解绑原因：manual 为手动移除，downvote 为投票下标，tag_deleted 为标签软删除",
    )
    """解绑原因：manual 为手动移除，downvote 为投票下标，tag_deleted 为标签软删除"""

    upvotes: int = Field(
        default=0, description="本轮当前正向票数；仅统计有效赞票，重新挂标从零开始"
    )
    """本轮当前正向票数；仅统计有效赞票，重新挂标从零开始"""

    downvotes: int = Field(
        default=0, description="本轮当前负向票数；负向票减正向票大于 5 时自动解绑"
    )
    """本轮当前负向票数；负向票减正向票大于 5 时自动解绑"""

    # 同一目标和标签仅允许一轮生效绑定，已结束的轮次保留为历史。
    __table_args__ = (
        Index(
            "uq_active_tag_binding",
            "target_type",
            "target_id",
            "tag_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index(
            "ix_tag_binding_active_reverse",
            "target_type",
            "tag_id",
            "target_id",
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("ix_tag_binding_history", "target_type", "target_id", "id"),
        CheckConstraint(
            "target_type IN ('thread', 'booklist') AND binding_source IN ('discord_sync', 'local') AND (binding_source <> 'discord_sync' OR target_type = 'thread') AND (binding_source <> 'discord_sync' OR discord_source_id IS NOT NULL) AND (binding_source <> 'local' OR discord_source_id IS NULL) AND upvotes >= 0 AND downvotes >= 0",
            name="ck_tag_binding",
        ),
    )
