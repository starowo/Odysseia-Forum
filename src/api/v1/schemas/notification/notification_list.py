from pydantic import BaseModel, Field

from api.v1.schemas.notification.notification_item import NotificationItem


class NotificationList(BaseModel):
    """分页动态通知列表。"""

    results: list[NotificationItem] = Field(description="当前页的动态通知列表")
    """当前页的动态通知列表"""

    total: int = Field(description="符合当前筛选条件的通知总数")
    """符合当前筛选条件的通知总数"""

    unread_count: int = Field(description="当前用户全部动态通知的未读数量")
    """当前用户全部动态通知的未读数量"""

    limit: int = Field(description="当前请求的分页大小")
    """当前请求的分页大小"""

    offset: int = Field(description="当前请求的分页偏移量")
    """当前请求的分页偏移量"""
