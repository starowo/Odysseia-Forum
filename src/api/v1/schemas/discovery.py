from typing import List
from pydantic import BaseModel, Field
from api.v1.schemas.search.thread_detail import ThreadDetail


class DiscoveryRailsResponse(BaseModel):
    """广场多轨道聚合响应体"""

    latest: List[ThreadDetail] = Field(description="最新发布")
    reaction_surge: List[ThreadDetail] = Field(description="近期点赞飙升")
    discussion_surge: List[ThreadDetail] = Field(description="近期讨论飙升")
    collection_surge: List[ThreadDetail] = Field(description="近期收藏飙升")
