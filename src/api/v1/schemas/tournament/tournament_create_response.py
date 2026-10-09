from pydantic import BaseModel, Field


class TournamentCreateResponse(BaseModel):
    """创建赛事书单响应"""

    message: str = Field("赛事书单创建成功", description="提示信息")
    """提示信息"""

    booklist_id: int = Field(..., description="书单ID")
    """书单ID"""

    title: str = Field(..., description="赛事标题")
    """赛事标题"""

    tournament_channel_id: int = Field(..., description="赛事频道ID")
    """赛事频道ID"""

    created: bool = Field(..., description="是否为新创建（false 表示已存在，幂等返回）")
    """是否为新创建（false 表示已存在，幂等返回）"""
