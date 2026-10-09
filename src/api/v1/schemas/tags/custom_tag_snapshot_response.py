from typing import Literal

from pydantic import Field

from api.v1.schemas.tags.tag_response import TagResponse


class CustomTagSnapshotResponse(TagResponse):
    """目标上的本地标签绑定及当前用户投票。"""

    source: Literal["discord", "custom"] = Field(
        description="标签实体来源，可为 discord 或 custom"
    )
    """标签实体来源，可为 discord 或 custom"""

    binding_source: Literal["local"] = Field(
        description="绑定来源，用于区分只读同步和本地治理"
    )
    """绑定来源判别字段"""

    readonly: Literal[False] = Field(
        description="固定为 false，自定义标签按权限进行治理"
    )
    """固定为 false，自定义标签按权限进行治理"""

    binding_id: str = Field(description="当前绑定轮次 ID，以十进制字符串返回")
    """当前绑定轮次 ID，以十进制字符串返回"""

    upvotes: int = Field(description="当前轮次正向票数")
    """当前轮次正向票数"""

    downvotes: int = Field(description="当前轮次负向票数")
    """当前轮次负向票数"""

    my_vote: Literal[-1, 0, 1] = Field(
        description="当前用户本轮投票：-1 为踩，0 为未投票，1 为赞"
    )
    """当前用户本轮投票：-1 为踩，0 为未投票，1 为赞"""
