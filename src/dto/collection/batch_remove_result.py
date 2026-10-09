from typing import List

from pydantic import BaseModel, Field


class BatchRemoveResult(BaseModel):
    """批量移除操作的结果"""

    removed_ids: List[int] = Field(..., description="成功移除的目标ID列表")
    removed_count: int = Field(..., description="成功移除的数量")
    not_found_count: int = Field(..., description="因未找到而未移除的数量")
