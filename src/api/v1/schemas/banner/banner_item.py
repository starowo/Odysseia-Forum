"""Banner项目Schema"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from shared.utc_datetime import UTCDateTime


class BannerItem(BaseModel):
    """Banner轮播项"""

    thread_id: int
    title: str
    cover_image_url: Optional[str] = None
    channel_id: int
    guild_id: int = Field(
        default=0,
        description="帖子所属服务器 ID（从索引帖读取，用于前端生成 Discord 链接）",
    )
    target_type: int = Field(default=1, description="论坛帖子 / 频道")
    start_time: Optional[UTCDateTime] = Field(
        default=None, description="Banner 展示开始时间"
    )
    end_time: Optional[UTCDateTime] = Field(
        default=None, description="Banner 展示结束时间"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("thread_id", "channel_id", "guild_id")
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)
