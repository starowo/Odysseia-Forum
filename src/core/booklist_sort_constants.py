"""Booklist 排序常量：列映射及默认值。"""

from models.booklist_item import BooklistItem
from models.thread import Thread
from shared.enum.booklist_sort_method import BooklistSortMethod
from shared.enum.booklist_sort_order import BooklistSortOrder

# 排序方法 → Thread / BooklistItem 列映射
# hot 不在其中 —— 它是复合公式排序，在 _apply_item_sorting 中单独处理
SORT_METHOD_COLUMN_MAP: dict[BooklistSortMethod, object] = {
    BooklistSortMethod.CREATED_AT: Thread.created_at,
    BooklistSortMethod.REACTION_COUNT: Thread.reaction_count,
    BooklistSortMethod.REPLY_COUNT: Thread.reply_count,
    BooklistSortMethod.COLLECTION_COUNT: Thread.collection_count,
    BooklistSortMethod.LAST_ACTIVE_AT: Thread.last_active_at,
    BooklistSortMethod.JOIN_TIME: BooklistItem.created_at,
    BooklistSortMethod.DISPLAY_ORDER: BooklistItem.display_order,
}

DEFAULT_SORT_METHOD = BooklistSortMethod.JOIN_TIME
DEFAULT_SORT_ORDER = BooklistSortOrder.DESC
