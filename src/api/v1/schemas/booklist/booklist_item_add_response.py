from pydantic import BaseModel, Field


class BooklistItemAddResponse(BaseModel):
    """添加帖子到书单成功响应"""

    message: str = Field(default="帖子已添加到书单", description="操作结果消息")
    booklist_item_id: int = Field(description="书单项ID")
    booklist_id: int = Field(description="书单ID")
    thread_id: int = Field(description="帖子ID")
    display_order: int = Field(description="排序权重")
