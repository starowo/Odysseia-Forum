from typing import List

from pydantic import BaseModel, Field, field_serializer

from dto.meta.tag_detail import TagDetail


class MappedSourceChannelDetail(BaseModel):
    """虚拟标签映射来源频道的详细信息"""

    guild_id: int = Field(description="所属服务器的 Discord ID")
    """所属服务器的 Discord ID"""

    channel_id: int = Field(description="频道的 Discord ID")
    """频道的 Discord ID"""

    channel_name: str = Field(description="频道名称")
    """频道名称"""

    available_tags: List[TagDetail] = Field(
        default_factory=list, description="该频道原生的可用标签"
    )
    """该频道原生的可用标签"""

    real_thread_count: int = Field(default=0, description="该频道的实际有效帖子数")
    """该频道的实际有效帖子数"""

    @field_serializer("guild_id", "channel_id")
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串以防前端 JS 精度丢失"""
        return str(value)
