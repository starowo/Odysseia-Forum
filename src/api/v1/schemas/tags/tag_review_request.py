from pydantic import BaseModel, Field


class TagReviewRequest(BaseModel):
    """作者对提议的裁定。"""

    approve: bool = Field(
        description="审核决定：true=同意添加，false=拒绝申请；同意时仍需校验标签状态、数量和互斥关系"
    )
    """审核决定：true 为同意添加，false 为拒绝申请"""
