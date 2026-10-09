from pydantic import BaseModel, Field


class DiscordTagSourceResponse(BaseModel):
    """标准概念当前有效的 DC 来源，历史来源通过审计追溯。"""

    id: str = Field(description="来源记录内部 ID")
    """来源记录内部 ID"""
    discord_tag_id: str = Field(description="Discord 原生标签 ID")
    """Discord 原生标签 ID"""
    channel_id: str | None = Field(
        description="来源频道 ID；历史未知频道为空，完整同步后补齐"
    )
    """来源频道 ID"""
    name: str = Field(description="DC 原始名称")
    """DC 原始名称"""
