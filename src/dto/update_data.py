from datetime import datetime
from typing import TypedDict


class UpdateData(TypedDict):
    """描述批量活动更新中的单个作品变化。"""

    increment: int
    last_active_at: datetime | None
