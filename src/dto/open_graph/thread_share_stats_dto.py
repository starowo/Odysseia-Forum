from pydantic import BaseModel, Field


class ThreadShareStatsDTO(BaseModel):
    """描述帖子分享卡片中的公开统计。"""

    reaction_count: int = Field(description="反应数")
    reply_count: int = Field(description="回复数")
    collection_count: int = Field(description="收藏数")
