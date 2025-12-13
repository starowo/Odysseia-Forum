from typing import List

from pydantic import BaseModel, Field


class BatchAddResult(BaseModel):
    """批量添加操作的结果"""

    added_ids: List[int] = Field(..., description="成功添加的目标ID列表")
    added_count: int = Field(..., description="成功添加的数量")
    duplicate_count: int = Field(..., description="因重复而未添加的数量")
