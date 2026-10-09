from pydantic import BaseModel, Field

from shared.utc_datetime import UTCDateTime


class OpenGraphWorkDTO(BaseModel):
    """描述作者或书单分享卡片中的代表作品。"""

    title: str = Field(description="作品标题")
    image_url: str = Field(description="当前有效的作品图片 URL")
    reaction_count: int = Field(description="作品反应数")
    created_at: UTCDateTime = Field(description="作品创建时间")
