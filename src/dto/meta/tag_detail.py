from typing import Optional
from pydantic import BaseModel, Field, field_serializer


class TagDetail(BaseModel):
    """标签的基础信息模型"""

    tag_id: int = Field(description="标签的 Discord ID")
    """标签的 Discord ID"""

    name: str = Field(description="标签名称")
    """标签名称"""

    @field_serializer("tag_id")
    def serialize_id(self, value: Optional[int]) -> Optional[str]:
        """序列化 ID 为字符串以防前端 JS 精度丢失"""
        return str(value) if value is not None else None
