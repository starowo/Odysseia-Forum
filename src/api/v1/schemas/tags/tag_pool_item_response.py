from pydantic import Field

from api.v1.schemas.tags.tag_response import TagResponse


class TagPoolItemResponse(TagResponse):
    """标签池中的标签及其检索别名。"""

    aliases: list[str] = Field(description="检索别名列表，无别名时为空数组")
    """检索别名列表，无别名时为空数组"""
