from pydantic import BaseModel, Field, field_serializer


class MarkReadResponse(BaseModel):
    """按作品标记动态通知已读的响应。"""

    thread_id: int | None = Field(default=None, description="作品 Discord ID")
    """作品 Discord ID；全部已读操作时为空"""

    marked_read: int = Field(description="本次实际标记为已读的通知数量")
    """本次实际标记为已读的通知数量"""

    @field_serializer("thread_id")
    def serialize_thread_id(self, value: int | None) -> str | None:
        """将 Discord ID 序列化为字符串。"""
        return str(value) if value is not None else None
