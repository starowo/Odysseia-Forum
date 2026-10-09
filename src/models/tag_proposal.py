from datetime import datetime

from sqlalchemy import BigInteger, Column, Index, text
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class TagProposal(SQLModel, table=True):
    """保存用户为帖子或书单添加标签的申请及审核结果。"""

    __tablename__ = "tag_proposal"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
        description="标签添加申请的内部主键",
    )
    """标签添加申请的内部主键"""

    target_type: str = Field(
        index=True, description="申请目标类型：thread 为帖子，booklist 为书单"
    )
    """申请目标类型：thread 为帖子，booklist 为书单"""

    target_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, index=True),
        description="申请目标 ID：帖子使用内部帖子 ID，书单使用内部书单 ID",
    )
    """申请目标 ID：帖子使用内部帖子 ID，书单使用内部书单 ID"""

    tag_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="申请添加的自定义标签内部 ID",
    )
    """申请添加的自定义标签内部 ID"""

    applicant_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, index=True),
        description="申请人的 Discord 用户 ID",
    )
    """申请人的 Discord 用户 ID"""

    owner_id: int = Field(
        sa_column=Column(BigInteger, nullable=False),
        description="提交申请时的帖子作者或书单所有者 Discord ID，用于发送审核通知",
    )
    """提交申请时的帖子作者或书单所有者 Discord ID，用于发送审核通知"""

    created_at: datetime = Field(
        default_factory=utc_now,
        description="申请提交时间（UTC），七天审核期限从此时开始",
    )
    """申请提交时间（UTC），七天审核期限从此时开始"""

    due_at: datetime = Field(
        index=True,
        description="自动审核到期时间（UTC），提交时间加七天，不受通知送达时间影响",
    )
    """自动审核到期时间（UTC），提交时间加七天，不受通知送达时间影响"""

    status: str = Field(
        default="pending",
        index=True,
        description="申请状态：pending 为待审核，approved 为通过，rejected 为拒绝，failed 为生效校验失败",
    )
    """申请状态：pending 为待审核，approved 为通过，rejected 为拒绝，failed 为生效校验失败"""

    reason: str | None = Field(
        default=None,
        description="裁定或失败原因：manual 为直接挂标，review 为人工审核，timeout 为超时通过；失败时保存业务原因码",
    )
    """裁定或失败原因：manual 为直接挂标，review 为人工审核，timeout 为超时通过；失败时保存业务原因码"""

    resolved_at: datetime | None = Field(
        default=None, description="申请处理完成时间（UTC）；待审核时为空"
    )
    """申请处理完成时间（UTC）；待审核时为空"""

    # 只限制待审核申请唯一，拒绝或手动删除后可以再次申请。
    __table_args__ = (
        Index(
            "uq_pending_tag_proposal",
            "target_type",
            "target_id",
            "tag_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )
