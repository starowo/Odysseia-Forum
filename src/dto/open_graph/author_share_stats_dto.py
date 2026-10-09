from pydantic import BaseModel, Field


class AuthorShareStatsDTO(BaseModel):
    """描述作者公开作品的聚合统计。"""

    thread_count: int = Field(description="公开作品数")
    reaction_count: int = Field(description="公开作品总反应数")
    reply_count: int = Field(description="公开作品总回复数")
