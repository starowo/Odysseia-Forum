from typing import Literal

from pydantic import BaseModel, Field

from api.v1.schemas.search import LatestUpdate, ThreadDetail
from shared.utc_datetime import UTCDateTime


class NotificationItem(BaseModel):
    """动态通知列表中的单项数据。"""

    id: int = Field(description="通知的数据库主键 ID")
    """通知的数据库主键 ID"""

    type: Literal["thread_update", "author_new_thread", "tag_review"] = Field(
        description="动态通知类型：thread_update=作品更新，author_new_thread=作者新作，tag_review=标签提议待审核"
    )
    """动态通知类型：作品更新、作者新作或标签提议待审核"""

    thread: ThreadDetail | None = Field(
        default=None, description="通知关联作品的完整信息；标签审核通知为空"
    )
    """通知关联作品的完整信息；标签审核通知为空"""

    target_type: str | None = Field(
        default=None,
        description="标签审核目标类型：thread=帖子，booklist=书单；其他通知为空",
    )
    """标签审核目标类型：帖子或书单；其他通知为空"""

    target_id: str | None = Field(
        default=None,
        description="标签审核目标 ID 的十进制字符串：帖子为 Discord 帖子 ID，书单为内部书单 ID；其他通知为空",
    )
    """标签审核目标 ID 字符串：Discord 帖子 ID 或内部书单 ID；其他通知为空"""

    proposal_id: str | None = Field(
        default=None,
        description="待审核标签申请的 ID 字符串，用于定位审核记录；其他通知为空",
    )
    """待审核标签申请的 ID 字符串；其他通知为空"""

    update: LatestUpdate | None = Field(
        default=None,
        description="作品更新详情；作者新作和标签审核通知为空",
    )
    """作品更新详情；作者新作和标签审核通知为空"""

    created_at: UTCDateTime = Field(description="通知产生时间")
    """通知产生时间"""

    read_at: UTCDateTime | None = Field(
        default=None,
        description="用户阅读时间；为空表示未读",
    )
    """用户阅读时间；为空表示未读"""
