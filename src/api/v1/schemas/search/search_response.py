from typing import List

from pydantic import Field

from api.v1.schemas.base import PaginatedResponse
from api.v1.schemas.search.thread_detail import ThreadDetail


class SearchResponse(PaginatedResponse[ThreadDetail]):
    """搜索接口的最终响应体"""

    available_tags: List[str] = Field(
        default_factory=list,
        description="当搜索单个频道时返回该频道的可用标签列表，全频道搜索时返回空列表",
    )
    virtual_tags: List[str] = Field(
        default_factory=list,
        description="当前频道配置的虚拟映射标签名列表（始终置顶于 available_tags 中）",
    )
