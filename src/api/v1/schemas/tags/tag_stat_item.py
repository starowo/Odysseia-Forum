from typing import List
from pydantic import BaseModel, Field
from api.v1.schemas.tags.channel_tag_info import ChannelTagInfo


class TagStatItem(BaseModel):
    """标签维度的聚合统计项"""

    tag_name: str = Field(description="标签名称")
    """标签名称"""

    is_abyss: bool = Field(description="是否为深渊向 TAG")
    """虚拟标签固定为 false"""

    source: str = Field(
        default="discord", description="统计分组来源：discord、custom 或 virtual"
    )
    """DC 按名称，自定义按分类和名称分组"""

    category: int | None = Field(
        default=None, description="自定义分类；原生或未分类时为空"
    )
    """统计分组的标签分类"""

    category_name: str | None = Field(default=None, description="分类中文名")
    """分类名称"""

    tag_ids: list[str] = Field(
        default_factory=list, description="本组实体内部 ID，均为字符串；虚拟标签为空"
    )
    """本组全部具体标签 ID，与 tag_name 对应"""

    total_thread_count: int = Field(description="该标签下的总帖子数(跨频道累加)")
    """该标签下的总帖子数(跨频道累加)"""

    channel_info: List[ChannelTagInfo] = Field(description="按频道分桶的详细统计数据")
    """按频道分桶的详细统计数据"""
