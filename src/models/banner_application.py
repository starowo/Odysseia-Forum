from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from shared.enum.application_status import ApplicationStatus


class BannerApplication(SQLModel, table=True):
    """Banner申请记录"""

    __tablename__ = "banner_application"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(index=True, description="帖子ID")
    channel_id: int = Field(index=True, description="帖子所在频道ID")
    applicant_id: int = Field(index=True, description="申请人Discord ID")
    cover_image_url: str = Field(description="封面图链接（21:9推荐）")
    target_scope: str = Field(
        index=True, description="目标范围：'global'表示全频道，或具体频道ID"
    )

    # 审核相关
    status: str = Field(
        default=ApplicationStatus.PENDING.value, index=True, description="申请状态"
    )
    applied_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="申请时间"
    )
    reviewed_at: Optional[datetime] = Field(default=None, description="审核时间")
    reviewer_id: Optional[int] = Field(default=None, description="审核员Discord ID")
    reject_reason: Optional[str] = Field(default=None, description="拒绝理由")

    # 审核记录消息ID（用于在指定thread中发送审核记录）
    review_message_id: Optional[int] = Field(default=None, description="审核记录消息ID")
    review_thread_id: Optional[int] = Field(
        default=None, description="审核记录所在的thread ID"
    )
