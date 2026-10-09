from pydantic import BaseModel, Field


class UnreadCountResponse(BaseModel):
    """动态通知未读数响应。"""

    unread_count: int = Field(description="当前用户全部动态通知的未读数量")
    """当前用户全部动态通知的未读数量"""
