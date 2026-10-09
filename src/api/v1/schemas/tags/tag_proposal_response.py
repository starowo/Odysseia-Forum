from typing import Literal

from pydantic import BaseModel, Field

from shared.utc_datetime import UTCDateTime


class TagProposalResponse(BaseModel):
    """标签提议的状态与审核时间。"""

    id: str = Field(description="提议内部 ID，以十进制字符串返回")
    """提议内部 ID，以十进制字符串返回"""

    tag_id: str = Field(description="提议标签内部 ID，以十进制字符串返回")
    """提议标签内部 ID，以十进制字符串返回"""

    tag_name: str = Field(description="申请标签的当前标准名")
    """申请标签标准名，历史操作名称见审计记录"""

    is_abyss: bool = Field(description="申请标签是否为深渊向 TAG")
    """申请标签的深渊向标识"""

    status: Literal["pending", "approved", "rejected", "failed"] = Field(
        description="pending 待审核，approved 通过，rejected 拒绝，failed 生效校验失败"
    )
    """pending 待审核，approved 通过，rejected 拒绝，failed 生效校验失败"""

    reason: str | None = Field(description="裁定或失败原因码；尚未裁定时为空")
    """裁定或失败原因码；尚未裁定时为空"""

    created_at: UTCDateTime = Field(description="提议创建时间（UTC）")
    """提议创建时间（UTC）"""

    due_at: UTCDateTime = Field(description="七天审核期限的到期时间（UTC）")
    """七天审核期限的到期时间（UTC）"""

    resolved_at: UTCDateTime | None = Field(
        description="处理完成时间（UTC）；待审核时为空"
    )
    """处理完成时间（UTC）；待审核时为空"""
