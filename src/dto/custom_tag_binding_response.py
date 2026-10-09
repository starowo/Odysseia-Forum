from typing import Literal

from pydantic import BaseModel, Field


class CustomTagBindingResponse(BaseModel):
    """帖子或书单当前生效的本地标签绑定信息。"""

    id: str = Field(description="标签内部 ID，以十进制字符串返回")
    """标签内部 ID"""

    name: str = Field(description="标签标准名，不含分类前缀")
    """标签标准名"""

    is_abyss: bool = Field(description="是否为深渊向 TAG；既有绑定仍正常展示")
    """是否为深渊向 TAG"""

    category: int | None = Field(
        description="分类枚举：1=癖好，2=作品，3=角色，4=特质，5=情节，6=背景，7=玩法"
    )
    """标签分类整数值"""

    category_name: str | None = Field(description="分类枚举对应的中文名称")
    """标签分类名称"""

    source: Literal["discord", "custom"] = Field(
        description="标签实体来源，与本地绑定来源独立"
    )
    """标签实体来源，与本地绑定独立"""

    enabled: bool = Field(description="标签是否启用；停用标签的现有绑定仍可展示")
    """标签池中的启用状态"""

    binding_id: str = Field(
        description="当前绑定轮次 ID，以十进制字符串返回；重新添加产生新轮次"
    )
    """当前标签绑定轮次 ID"""

    upvotes: int = Field(description="当前绑定轮次的正向票数")
    """当前轮次正向票数"""

    downvotes: int = Field(description="当前绑定轮次的负向票数")
    """当前轮次负向票数"""

    binding_source: Literal["local"] = Field(
        default="local",
        description="绑定来源固定为 local；即使标签来源为 DC，也按本地权限治理",
    )
    """本地绑定来源"""
    readonly: Literal[False] = Field(
        default=False, description="本地绑定不是 DC 只读绑定；仍需按当前用户权限操作"
    )
    """绑定是否只读"""
