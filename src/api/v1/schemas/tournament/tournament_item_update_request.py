from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TournamentItemUpdateRequest(BaseModel):
    """更新赛事项请求体"""

    comment: Optional[str] = Field(None, description="推荐语/备注")
    """推荐语/备注"""
    tournament_participated_at: Optional[datetime] = Field(None, description="参赛时间")
    """参赛时间"""
