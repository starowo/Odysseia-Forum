"""BooklistItem 数据传输对象 — 安全用于 session 外。"""

from typing import Optional

from pydantic import BaseModel, Field


class BooklistItemDTO(BaseModel):
    """BooklistItem 的轻量 DTO。"""

    id: Optional[int] = Field(default=None, description="主键 ID")
    booklist_id: int = Field(description="所属书单 ID")
    thread_id: int = Field(description="关联的帖子 ID")
    display_order: int = Field(default=0, description="排序序号")
    comment: Optional[str] = Field(default=None, description="书单主对该帖子的备注")

    @staticmethod
    def from_orm(item) -> "BooklistItemDTO":
        """从 BooklistItem ORM 对象构建 BooklistItemDTO（须在 session 内调用）。"""
        return BooklistItemDTO(
            id=item.id,
            booklist_id=item.booklist_id,
            thread_id=item.thread_id,
            display_order=item.display_order,
            comment=item.comment,
        )
