from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints

from shared.tag_description import TagDescription


class TagCreateRequest(BaseModel):
    """创建标准标签所需的完整参数。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=100,
        description="标签标准名，不含分类前缀；同名概念使用括号后缀限定上下文",
    )
    """标签标准名，不含分类前缀；同名概念使用括号后缀消歧"""

    description: TagDescription = Field(
        default="", description="标签含义的纯文本说明，最多 2000 字；空字符串表示未填写"
    )
    """标签含义说明；清理首尾空白、保留内部换行，默认空字符串"""

    category: int = Field(
        ge=1,
        le=7,
        description="分类枚举：1=癖好，2=作品，3=角色，4=特质，5=情节，6=背景，7=玩法",
    )
    """分类整数值：癖好、作品、角色、特质、情节、背景、玩法依次为 1 至 7"""

    is_abyss: StrictBool = Field(
        default=False, description="是否为深渊向 TAG；默认创建为正常向"
    )
    """是否为深渊向 TAG"""

    aliases: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
        ]
    ] = Field(
        default_factory=list,
        max_length=100,
        description="检索别名列表，可被多个标准标签共用；未传时不添加别名",
    )
    """检索别名列表，可与其他标准标签重名；默认空列表"""
