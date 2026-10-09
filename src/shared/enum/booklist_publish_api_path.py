"""书单发布服务 API 路径枚举"""

from enum import StrEnum


class BooklistPublishApiPath(StrEnum):
    """书单发布服务 API 路径"""

    PUBLISH = "/booklist/publish"
    """发布或更新书单"""

    UNPUBLISH = "/booklist/unpublish"
    """取消发布书单"""
