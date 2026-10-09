from typing import List

from pydantic import BaseModel, Field, field_serializer


class VirtualTagDetail(BaseModel):
    """虚拟标签详细信息模型"""

    tag_name: str = Field(description="虚拟标签名称")
    """虚拟标签名称"""

    source_channel_ids: List[int] = Field(description="此虚拟标签的来源频道 ID 列表")
    """此虚拟标签的来源频道 ID 列表"""

    @field_serializer("source_channel_ids")
    def serialize_ids(self, value: List[int]) -> List[str]:
        """将 Discord ID 序列化为字符串以防前端 JS 精度丢失"""
        return [str(v) for v in value]
