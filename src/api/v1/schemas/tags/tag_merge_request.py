from pydantic import BaseModel, Field
from shared.request_id import PositiveRequestId


class TagMergeRequest(BaseModel):
    """提交需保留的标准标签和已确认的预检版本。"""

    target_tag_id: PositiveRequestId = Field(
        description="合并后保留的标签内部 ID；涉及 DC 概念时必须保留 DC 标签"
    )
    """保留的标准标签 ID"""
    version: str = Field(
        description="合并预检返回的版本，原样提交；数据变化返回 409，需重新预检"
    )
    """预检确认版本"""
