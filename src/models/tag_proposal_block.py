from datetime import datetime

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel

from shared.time_utils import utc_now


class TagProposalBlock(SQLModel, table=True):
    """保存投票下标后的永久重提限制，作者和管理组仍可直接挂标。"""

    __tablename__ = "tag_proposal_block"

    target_type: str = Field(
        primary_key=True, description="被限制的目标类型：thread 为帖子，booklist 为书单"
    )
    """被限制的目标类型：thread 为帖子，booklist 为书单"""

    target_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="被限制的目标 ID：帖子使用内部帖子 ID，书单使用内部书单 ID",
    )
    """被限制的目标 ID：帖子使用内部帖子 ID，书单使用内部书单 ID"""

    tag_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True),
        description="曾在此目标被投票移除的标签内部 ID；软删除与恢复不会清除此限制",
    )
    """曾在此目标被投票移除的标签内部 ID；软删除与恢复不会清除此限制"""

    created_at: datetime = Field(
        default_factory=utc_now, description="首次记录投票移除限制的时间（UTC）"
    )
    """首次记录投票移除限制的时间（UTC）"""
