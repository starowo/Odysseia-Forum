from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from shared.request_id import PositiveRequestId


class TagRelationRequest(BaseModel):
    """创建一条直接标签关系的必要参数。"""

    model_config = ConfigDict(extra="forbid")

    target_tag_id: PositiveRequestId = Field(
        description="关系目标标签的内部 ID，不是 Discord 标签 ID；包含关系中表示父标签",
    )
    """关系目标标签的内部 ID；包含关系中为父标签"""

    kind: Literal["implies", "excludes"] = Field(
        description="关系类型：implies=有向包含关系，excludes=对称互斥关系"
    )
    """关系类型：implies 为有向包含，excludes 为对称互斥"""
