"""Banner项目Schema"""

from pydantic import BaseModel, field_serializer


class BannerItem(BaseModel):
    """Banner轮播项"""

    thread_id: int
    title: str
    cover_image_url: str
    channel_id: int

    class Config:
        from_attributes = True

    @field_serializer("thread_id", "channel_id")
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)
