from typing import List, Optional

from pydantic import BaseModel


class UserSearchPreferencesDTO(BaseModel):
    """用于传输用户搜索偏好设置的数据传输对象。"""

    user_id: int
    # 频道偏好
    preferred_channels: Optional[List[int]] = None

    # 作者偏好
    include_authors: Optional[List[int]] = None
    exclude_authors: Optional[List[int]] = None

    # 标签偏好
    include_tags: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None

    # 关键词偏好
    include_keywords: str = ""
    exclude_keywords: str = ""
    exclude_keyword_exemption_markers: List[str] = ["禁", "🈲"]

    # 时间偏好
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    active_after: Optional[str] = None
    active_before: Optional[str] = None

    # 显示偏好
    preview_image_mode: str = "thumbnail"
    results_per_page: int = 5

    # 排序算法偏好
    sort_method: str = "comprehensive"

    # 自定义排序的基础算法
    custom_base_sort: str = "comprehensive"

    class Config:
        from_attributes = True
