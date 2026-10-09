from typing import Optional

from pydantic import Field

from api.v1.schemas.booklist.booklist_publish_info import BooklistPublishInfo
from api.v1.schemas.booklist.booklist_summary import BooklistSummary


class BooklistDetail(BooklistSummary):
    """书单详情（继承摘要，附加发布信息）"""

    publish_info: Optional[BooklistPublishInfo] = Field(
        None, description="发布信息（仅已发布书单返回）"
    )
    """发布信息（仅已发布书单返回）"""
