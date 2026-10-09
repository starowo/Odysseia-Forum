from pydantic import BaseModel, Field

from shared.utc_datetime import UTCDateTime


class OpenGraphLatestWorkDTO(BaseModel):
    """描述作者最新公开作品的最小信息。"""

    title: str = Field(description="作品标题")
    created_at: UTCDateTime = Field(description="作品创建时间")
