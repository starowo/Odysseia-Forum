from datetime import datetime

from pydantic import BaseModel


class AuthorShareQueryDTO(BaseModel):
    """承载作者 Repository 返回的脱离 Session 的分享数据。"""

    display_name: str | None
    avatar_url: str | None
    last_updated: datetime
