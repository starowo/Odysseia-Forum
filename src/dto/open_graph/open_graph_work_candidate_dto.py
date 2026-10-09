from datetime import datetime

from pydantic import BaseModel, Field


class OpenGraphWorkCandidateDTO(BaseModel):
    """承载 Repository 流式返回的代表作品候选。"""

    thread_id: int = Field(description="Discord 帖子 ID，仅供内部处理")
    title: str
    thumbnail_urls: list[str] = Field(default_factory=list)
    reaction_count: int
    created_at: datetime
