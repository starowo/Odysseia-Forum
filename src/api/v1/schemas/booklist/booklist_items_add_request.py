from typing import List
from pydantic import BaseModel
from src.api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData


class BooklistItemsAddRequest(BaseModel):
    items: List[BooklistItemAddData]
