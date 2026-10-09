"""书单帖子排序顺序枚举"""

from enum import Enum


class BooklistSortOrder(str, Enum):
    """书单帖子排序顺序"""

    ASC = "asc"
    DESC = "desc"
