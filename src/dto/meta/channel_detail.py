from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from dto.meta.tag_detail import TagDetail
from dto.meta.virtual_tag_detail import VirtualTagDetail
from dto.meta.mapped_source_channel_detail import MappedSourceChannelDetail


class ChannelDetail(BaseModel):
    """频道的元数据模型"""

    guild_id: int = Field(description="所属服务器的 Discord ID")
    """所属服务器的 Discord ID"""

    guild_name: str = Field(default="未知服务器", description="服务器名称")
    """服务器名称"""

    channel_id: int = Field(description="频道的 Discord ID")
    """频道的 Discord ID"""

    channel_name: str = Field(alias="name", description="频道名称")
    """频道名称"""

    category_id: Optional[int] = Field(
        default=None, description="频道所属类别的 Discord ID"
    )
    """频道所属类别的 Discord ID"""

    category_name: Optional[str] = Field(default=None, description="频道所属类别名称")
    """频道所属类别名称"""

    available_tags: List[TagDetail] = Field(
        default_factory=list, description="该频道原生的可用标签"
    )
    """该频道原生的可用标签"""

    virtual_tags: List[VirtualTagDetail] = Field(
        default_factory=list, description="映射到该频道的虚拟标签"
    )
    """映射到该频道的虚拟标签"""

    mapped_source_channels: List[MappedSourceChannelDetail] = Field(
        default_factory=list, description="虚拟标签的来源频道详细信息"
    )
    """虚拟标签的来源频道详细信息"""

    real_thread_count: int = Field(
        default=0, description="实际帖子数（频道内真实存在的帖子总数）"
    )
    """实际帖子数"""

    virtual_thread_count: int = Field(
        default=0, description="虚拟标签映射帖子数（来自映射频道的帖子总数）"
    )
    """虚拟标签映射帖子数"""

    total_thread_count: int = Field(
        default=0, description="总帖子数（实际帖子数 + 虚拟标签映射帖子数）"
    )
    """总帖子数"""

    @field_serializer("guild_id", "channel_id", "category_id")
    def serialize_id(self, value: Optional[int]) -> Optional[str]:
        """序列化频道/服务器 ID 为字符串以防前端 JS 精度丢失"""
        return str(value) if value is not None else None

    model_config = ConfigDict(populate_by_name=True)
