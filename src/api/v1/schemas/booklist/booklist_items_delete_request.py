from typing import List
from pydantic import BaseModel


class BooklistItemsDeleteRequest(BaseModel):
    thread_ids: List[int]
