from typing import Optional
from pydantic import BaseModel, Field, field_serializer


class ChannelThreadCount(BaseModel):
    """频道帖子统计聚合结果"""

    channel_id: int = Field(description="频道 ID")
    """频道 ID"""

    thread_count: int = Field(description="有效帖子总数")
    """有效帖子总数"""

    @field_serializer("channel_id")
    def serialize_id(self, value: Optional[int]) -> Optional[str]:
        """序列化 ID 为字符串以防前端 JS 精度丢失"""
        return str(value) if value is not None else None
