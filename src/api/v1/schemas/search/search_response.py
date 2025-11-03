from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime

from api.v1.schemas.search.thread_detail import ThreadDetail
from ..base import PaginatedResponse
from .author import AuthorDetail
from ..banner import BannerItem


class SearchResponse(PaginatedResponse[ThreadDetail]):
    """搜索接口的最终响应体"""

    available_tags: List[str] = Field(
        default_factory=list,
        description="当搜索单个频道时返回该频道的可用标签列表，全频道搜索时返回空列表",
    )
    banner_carousel: List[BannerItem] = Field(
        default_factory=list,
        description="Banner轮播列表，包含当前频道+全频道的banner（最多8个）",
    )
    unread_count: int = Field(default=0, description="当前用户关注列表的未读更新数量")
