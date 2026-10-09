from pydantic import BaseModel, Field

from api.v1.schemas.search import AuthorDetail
from shared.utc_datetime import UTCDateTime


class AuthorFollowItem(BaseModel):
    """关注作者列表中的单项数据。"""

    author: AuthorDetail = Field(description="被关注作者的详细信息")
    """被关注作者的详细信息"""

    followed_at: UTCDateTime = Field(description="最近一次关注该作者的时间")
    """最近一次关注该作者的时间"""

    active: bool = Field(description="当前是否仍在关注该作者")
    """当前是否仍在关注该作者"""
