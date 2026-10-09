from typing import Optional
from pydantic import BaseModel, Field, field_serializer


class ChannelTagInfo(BaseModel):
    """标签在某个频道下的统计信息"""

    guild_id: int = Field(description="频道所属服务器的 Discord ID")
    """频道所属服务器的 Discord ID"""

    guild_name: str = Field(default="未知服务器", description="服务器名称")
    """服务器名称"""

    channel_id: int = Field(description="频道的 Discord ID")
    """频道的 Discord ID"""

    channel_name: str = Field(default="未知频道", description="频道名称")
    """频道名称"""

    category_id: Optional[int] = Field(
        default=None, description="频道所属类别的 Discord ID"
    )
    """频道所属类别的 Discord ID"""

    category_name: Optional[str] = Field(default=None, description="频道所属类别名称")
    """频道所属类别名称"""

    tag_ids: list[str] = Field(
        default_factory=list,
        description="该频道分组包含的全部标签内部 ID；tag_id 仅保留代表 ID 兼容旧端",
    )
    """分组实体 ID 列表"""

    tag_id: int = Field(
        description="分组代表标签的内部 ID（虚拟标签为 0），完整集合见 tag_ids"
    )
    """分组代表标签的内部 ID（虚拟标签为 0），完整集合见 tag_ids"""

    thread_count: int = Field(description="该频道下包含此标签的帖子数量")
    """该频道下包含此标签的帖子数量"""

    is_virtual: bool = Field(description="是否为虚拟映射标签")
    """是否为虚拟映射标签"""

    @field_serializer("guild_id", "channel_id", "tag_id", "category_id")
    def serialize_ids(self, value: Optional[int]) -> Optional[str]:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value) if value is not None else None
