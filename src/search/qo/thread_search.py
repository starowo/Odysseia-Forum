from dataclasses import dataclass, field
from typing import Optional, List
from shared.enum.default_preferences import DefaultPreferences


@dataclass
class ThreadSearchQuery:
    """封装所有搜索条件的查询对象"""

    channel_ids: Optional[List[int]] = None
    include_tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    keywords: Optional[str] = None
    exclude_keywords: Optional[str] = None
    exclude_keyword_exemption_markers: Optional[List[str]] = None
    include_authors: Optional[List[int]] = None
    exclude_authors: Optional[List[int]] = None
    author_name: Optional[str] = None
    tag_logic: str = "and"
    sort_method: str = "comprehensive"
    sort_order: str = "desc"

    custom_base_sort: str = "comprehensive"
    reaction_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    reply_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    active_after: Optional[str] = None
    active_before: Optional[str] = None

    # 指定为哪个用户搜索收藏
    user_id_for_collection_search: Optional[int] = None
