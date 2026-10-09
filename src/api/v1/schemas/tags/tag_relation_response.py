from typing import Literal

from pydantic import BaseModel, Field


class TagRelationResponse(BaseModel):
    """标签之间的一条直接关系。"""

    source_id: str = Field(description="起点标签内部 ID，以十进制字符串返回")
    """起点标签内部 ID，以十进制字符串返回"""

    target_id: str = Field(description="终点标签内部 ID，以十进制字符串返回")
    """终点标签内部 ID，以十进制字符串返回"""

    kind: Literal["implies", "excludes"] = Field(
        description="implies 为有向包含，excludes 为对称互斥"
    )
    """implies 为有向包含，excludes 为对称互斥"""
