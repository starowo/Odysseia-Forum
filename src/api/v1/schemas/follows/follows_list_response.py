"""关注列表的 API 响应体"""

from typing import List

from pydantic import BaseModel, Field

from api.v1.schemas.follows.followed_thread_response import FollowedThreadResponse


class FollowsListResponse(BaseModel):
    """关注列表的 API 响应体"""

    total: int = Field(description="关注总数")
    threads: List[FollowedThreadResponse] = Field(description="帖子列表")
    limit: int = Field(description="返回数量限制")
    offset: int = Field(description="偏移量")
