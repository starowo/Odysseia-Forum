from pydantic import BaseModel, Field


class BooklistUpdateResponse(BaseModel):
    """更新书单成功响应"""

    message: str = Field(default="书单更新成功", description="操作结果消息")
    booklist_id: int = Field(description="更新的书单ID")
    title: str = Field(description="更新后的书单标题")
