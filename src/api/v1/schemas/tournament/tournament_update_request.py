from typing import Optional

from pydantic import BaseModel, Field


class TournamentUpdateRequest(BaseModel):
    """更新赛事书单请求"""

    title: Optional[str] = Field(None, description="赛事标题")
    description: Optional[str] = Field(None, description="赛事简介")
    cover_image_url: Optional[str] = Field(None, description="封面图URL")
    is_public: Optional[bool] = Field(None, description="是否公开")
