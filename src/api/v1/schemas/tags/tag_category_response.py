from pydantic import BaseModel, Field


class TagCategoryResponse(BaseModel):
    """稳定的标签分类枚举项。"""

    value: int = Field(
        description="分类值：1=癖好，2=作品，3=角色，4=特质，5=情节，6=背景，7=玩法"
    )
    """分类值：1=癖好，2=作品，3=角色，4=特质，5=情节，6=背景，7=玩法"""

    name: str = Field(description="分类中文名称")
    """分类中文名称"""
