from typing import List

from pydantic import BaseModel, Field

from api.v1.schemas.tags.tag_stat_item import TagStatItem


class TagStatsResponse(BaseModel):
    """标签聚合统计的完整响应体"""

    total_threads: int = Field(description="检索范围内的有效帖子总数")
    """检索范围内的有效帖子总数"""

    items: List[TagStatItem] = Field(description="各个标签的聚合统计列表")
    """各个标签的聚合统计列表"""
