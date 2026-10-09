from typing import List, Optional, Set

from pydantic import BaseModel, Field


class ChannelMappingResolutionDTO(BaseModel):
    """频道映射解析结果的数据传输对象"""

    effective_channel_ids: Optional[List[int]] = Field(
        default=None,
        description="传入 SQL 查询的频道 ID 列表；None 表示不限制频道",
    )
    """传入 SQL 查询的频道 ID 列表；None 表示不限制频道"""

    effective_include_tags: List[str] = Field(
        default_factory=list,
        description="过滤掉虚拟标签后传给数据库的真实正选标签",
    )
    """过滤掉虚拟标签后传给数据库的真实正选标签"""

    effective_exclude_tags: List[str] = Field(
        default_factory=list,
        description="过滤掉虚拟标签后传给数据库的真实反选标签",
    )
    """过滤掉虚拟标签后传给数据库的真实反选标签"""

    searched_ids: Set[int] = Field(
        default_factory=set,
        description="逻辑上覆盖的真实频道 ID 集合（永不为空），用于构建前端可用标签列表等下游消费",
    )
    """逻辑上覆盖的真实频道 ID 集合（永不为空），用于构建前端可用标签列表等下游消费"""

    has_mapping: bool = Field(
        default=False,
        description="本次查询是否触发了频道映射（虚拟标签）解析",
    )
    """本次查询是否触发了频道映射（虚拟标签）解析"""
