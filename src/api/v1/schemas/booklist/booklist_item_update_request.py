from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BooklistItemUpdateRequest(BaseModel):
    """更新书单项请求体"""

    comment: Optional[str] = Field(None, description="推荐语/备注")
    """推荐语/备注"""
    display_order: Optional[int] = Field(None, description="排序权重")
    """排序权重"""
    tournament_participated_at: Optional[datetime] = Field(
        None, description="参赛时间（赛事专用）"
    )
    """参赛时间（赛事专用）"""
