from pydantic import BaseModel, Field


class AuthorStats(BaseModel):
    """作者统计摘要的响应模型。"""

    thread_count: int = Field(default=0, description="发帖总数")
    """发帖总数"""

    reaction_count: int = Field(default=0, description="收到的总反应数")
    """收到的总反应数"""

    reply_count: int = Field(default=0, description="收到的总回复数")
    """收到的总回复数"""
