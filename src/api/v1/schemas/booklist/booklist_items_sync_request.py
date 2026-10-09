from typing import List, Optional

from pydantic import BaseModel, Field


class BooklistItemsSyncRequest(BaseModel):
    """批量同步帖子在多个书单中的存在性"""

    thread_id: int = Field(description="帖子ID")
    scope_booklist_ids: List[int] = Field(description="操作范围：要检查的书单ID列表")
    target_booklist_ids: List[int] = Field(
        description="修改后应包含该帖子的书单ID列表（必须是 scope 的子集）"
    )
    comment: Optional[str] = Field(default=None, description="推荐语/备注")
