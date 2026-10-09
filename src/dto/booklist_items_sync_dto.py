from typing import List

from pydantic import BaseModel, Field


class BooklistItemsSyncDTO(BaseModel):
    """批量同步书单项的结果。"""

    thread_id: int = Field(description="帖子ID")
    added_to_booklist_ids: List[int] = Field(
        default_factory=list, description="新增了帖子的书单ID"
    )
    removed_from_booklist_ids: List[int] = Field(
        default_factory=list, description="移除了帖子的书单ID"
    )
    unchanged_booklist_ids: List[int] = Field(
        default_factory=list, description="未变更的书单ID"
    )
