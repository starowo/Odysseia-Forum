from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ThreadUpdateDTO:
    """跨边界传递已发布更新的数据。"""

    id: int
    thread_id: int
    message_id: int | None
    publisher_id: int
    description: str
    version: str | None
    source_message_at: datetime
    published_at: datetime
    overview_message_id: int | None
