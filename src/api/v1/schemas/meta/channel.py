from pydantic import BaseModel, Field, field_serializer
from typing import List
from .tag_detail import TagDetail


class Channel(BaseModel):
    """用于 API 响应的频道及其包含的可用标签"""

    id: int = Field(description="频道的 Discord ID")
    name: str = Field(description="频道的名称")
    tags: List[TagDetail] = Field(description="该频道下所有可用的标签列表")

    @field_serializer('id')
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)
