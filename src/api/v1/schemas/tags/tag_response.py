from typing import Literal

from pydantic import BaseModel, Field

from api.v1.schemas.tags.discord_tag_source_response import DiscordTagSourceResponse
from shared.utc_datetime import UTCDateTime


class TagResponse(BaseModel):
    """标签实体的公开基本信息。"""

    id: str = Field(description="标签内部 ID，以十进制字符串返回")
    """标签内部 ID，以十进制字符串返回"""

    name: str = Field(description="标准名，不含分类前缀")
    """标准名，不含分类前缀"""

    description: str = Field(
        default="", description="标签含义的纯文本说明；未填写时为空字符串"
    )
    """标签含义的纯文本说明；未填写时返回空字符串"""

    is_abyss: bool = Field(
        description="是否为深渊向 TAG；该标识不改变既有绑定的展示"
    )
    """是否为深渊向 TAG"""

    source: Literal["discord", "custom"] = Field(
        description="来源：discord 为原生标签，custom 为自定义标签"
    )
    """来源：discord 为原生标签，custom 为自定义标签"""

    discord_sources: list[DiscordTagSourceResponse] = Field(
        default_factory=list,
        description="当前有效 DC 来源列表；标准概念可对应多个频道，不再提供单个 discord_tag_id",
    )
    """标准概念的有效来源列表"""

    category: int | None = Field(
        description="分类枚举值 1–7；DC 概念和转换标签可暂未分类，为空时显示未分类"
    )
    """分类枚举值 1–7；DC 概念和转换标签可暂未分类，为空时显示未分类"""

    category_name: str | None = Field(description="分类中文名；未分类时为空")
    """分类中文名；未分类时为空"""

    enabled: bool = Field(description="标签是否启用")
    """标签是否启用"""

    deleted_at: UTCDateTime | None = Field(
        description="软删除时间（UTC）；未删除时为空"
    )
    """软删除时间（UTC）；未删除时为空"""
