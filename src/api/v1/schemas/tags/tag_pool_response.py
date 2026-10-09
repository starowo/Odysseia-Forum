from pydantic import BaseModel, Field

from api.v1.schemas.tags.tag_pool_item_response import TagPoolItemResponse


class TagPoolResponse(BaseModel):
    """返回当前筛选条件下的完整标签池。"""

    results: list[TagPoolItemResponse] = Field(description="完整标签列表")
    """完整标签列表"""

    total: int = Field(description="当前权限与筛选条件下的标签总数")
    """当前权限与筛选条件下的标签总数，始终等于 results 长度"""
