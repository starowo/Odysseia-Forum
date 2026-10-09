from datetime import datetime

from pydantic import BaseModel


class BooklistShareQueryDTO(BaseModel):
    """承载书单 Repository 返回的脱离 Session 的分享数据。"""

    owner_id: int
    title: str
    description: str | None
    cover_image_url: str | None
    is_anonymous: bool
    is_tournament: bool
    collection_count: int
    view_count: int
    created_at: datetime
    updated_at: datetime
