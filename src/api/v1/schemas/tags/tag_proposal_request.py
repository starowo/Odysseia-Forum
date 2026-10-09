from pydantic import BaseModel, Field
from shared.request_id import PositiveRequestId


class TagProposalRequest(BaseModel):
    """单标签提议请求。"""

    tag_id: PositiveRequestId = Field(
        description="提议添加的标签内部 ID，必须来自可用标签池；帖子仅允许自定义实体，书单也允许 DC 实体；接受十进制字符串或整数，非 Discord 标签 ID"
    )
    """提议添加的标签内部 ID；书单可使用 DC 标签实体"""
