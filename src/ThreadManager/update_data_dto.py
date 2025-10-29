from datetime import datetime
from typing import TypedDict


class UpdateData(TypedDict):
    increment: int
    last_active_at: datetime | None
