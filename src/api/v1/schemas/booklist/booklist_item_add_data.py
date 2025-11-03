from typing import Optional
from pydantic import BaseModel


class BooklistItemAddData(BaseModel):
    thread_id: int
    comment: Optional[str] = None
    display_order: Optional[int] = None
