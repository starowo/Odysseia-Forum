from pydantic import BaseModel, Field

from api.v1.schemas.author_follow.author_follow_item import AuthorFollowItem


class AuthorFollowList(BaseModel):
    """分页作者关注列表。"""

    results: list[AuthorFollowItem] = Field(description="当前页的作者关注关系列表")
    """当前页的作者关注关系列表"""

    total: int = Field(description="符合当前筛选条件的作者关注总数")
    """符合当前筛选条件的作者关注总数"""

    limit: int = Field(description="当前请求的分页大小")
    """当前请求的分页大小"""

    offset: int = Field(description="当前请求的分页偏移量")
    """当前请求的分页偏移量"""
