from datetime import datetime

from pydantic import BaseModel, Field


class BooklistCreateResponse(BaseModel):
    """创建书单成功响应"""

    message: str = Field(default="书单创建成功", description="操作结果消息")
    booklist_id: int = Field(description="新创建的书单ID")
    title: str = Field(description="书单标题")
    created_at: datetime = Field(description="创建时间")
