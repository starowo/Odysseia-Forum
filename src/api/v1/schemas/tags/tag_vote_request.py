from typing import Literal

from pydantic import BaseModel, Field


class TagVoteRequest(BaseModel):
    """幂等设置单个轮次的当前投票。"""

    vote: Literal[-1, 0, 1] = Field(
        description="当前挂标轮次的本人投票：1=赞，-1=踩，0=撤票；重复提交同值不重复计票"
    )
    """当前轮次的本人投票：1 为赞，-1 为踩，0 为撤票"""
