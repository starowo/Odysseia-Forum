from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from shared.utc_datetime import UTCDateTime


class BooklistPublishInfo(BaseModel):
    """书单发布信息（仅详情接口返回）"""

    guild_id: int = Field(description="Discord 服务器 ID")
    """Discord 服务器 ID"""

    thread_id: int = Field(description="Discord 讨论帖 ID")
    """Discord 讨论帖 ID"""

    thread_url: str = Field(description="Discord 讨论帖完整 URL")
    """Discord 讨论帖完整 URL"""

    message_id: Optional[int] = Field(None, description="已发布的 Discord 消息 ID")
    """已发布的 Discord 消息 ID """

    message_url: Optional[str] = Field(None, description="已发布的 Discord 消息 URL")
    """已发布的 Discord 消息 URL"""

    published_at: UTCDateTime = Field(description="发布时间")
    """发布时间"""

    @field_serializer("guild_id", "thread_id", "message_id")
    def serialize_ids(self, value: int | None) -> str | None:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        if value is None:
            return None
        return str(value)
