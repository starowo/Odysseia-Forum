from typing import Optional

from pydantic import BaseModel, Field


class TournamentCreateRequest(BaseModel):
    """创建赛事书单请求"""

    tournament_channel_id: int = Field(..., description="赛事关联的 Discord 频道ID")
    """赛事关联的 Discord 频道ID"""

    owner_id: int = Field(..., description="赛事举办者 Discord 用户ID（即书单 owner）")
    """赛事举办者 Discord 用户ID（即书单 owner）"""

    title: str = Field(..., description="赛事标题")
    """赛事标题"""

    description: Optional[str] = Field(None, description="赛事简介")
    """赛事简介"""

    cover_image_url: Optional[str] = Field(None, description="封面图URL")
    """封面图URL"""

    is_public: bool = Field(True, description="是否公开")
    """是否公开"""
