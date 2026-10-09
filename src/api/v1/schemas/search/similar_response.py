from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from api.v1.schemas.search.thread_detail import ThreadDetail


class SimilarThreadsResponse(BaseModel):
    """相似帖子推荐接口的响应体"""

    source_thread_id: int = Field(description="源帖子的 Discord ID")
    """源帖子的 Discord ID"""

    matched_tag_count: int = Field(
        default=0,
        description="最后一级命中使用的 TAG 数量（越大代表相似度越高）；若为 0 说明未按 TAG 匹配到任何结果",
    )
    """最后一级命中使用的 TAG 数量"""

    results: List[ThreadDetail] = Field(
        default_factory=list, description="推荐的相似帖子列表（最多 limit 条）"
    )
    """推荐的相似帖子列表"""

    @field_serializer("source_thread_id")
    def serialize_source_thread_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)

    model_config = ConfigDict(from_attributes=True)
