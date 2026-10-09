from dataclasses import dataclass, field
from typing import List, Optional

from shared.enum import DefaultPreferences


@dataclass
class ThreadSearchQuery:
    """封装所有搜索条件的查询对象"""

    guild_id: Optional[int] = None
    """Discord 服务器 ID，用于按服务器筛选帖子"""

    channel_ids: Optional[List[int]] = None
    """Discord 频道 ID 列表，用于按频道筛选帖子"""

    exclude_channel_ids: Optional[List[int]] = None
    """要排除的 Discord 频道 ID 列表（如深渊区频道）"""

    include_tags: List[str] = field(default_factory=list)
    """包含的标签名称列表，帖子必须包含这些标签"""

    include_tag_ids: list[int] = field(default_factory=list)
    """包含的内部标签 ID 列表，可混合原生与自定义标签，按 tag_logic 统一匹配"""

    exclude_tag_ids: list[int] = field(default_factory=list)
    """排除的内部标签 ID 列表，命中任意原生或自定义标签即排除帖子"""

    exclude_tags: List[str] = field(default_factory=list)
    """排除的标签名称列表，帖子不能包含这些标签"""

    keywords: Optional[str] = None
    """搜索关键词"""

    exclude_keywords: Optional[str] = None
    """排除关键词，帖子内容不能包含这些关键词"""

    exclude_keyword_exemption_markers: Optional[List[str]] = None
    """排除关键词的豁免标记，当关键词附近出现这些标记时，该关键词不生效"""

    include_authors: Optional[List[int]] = None
    """包含的作者 ID 列表，帖子作者必须在此列表中"""

    exclude_authors: Optional[List[int]] = None
    """排除的作者 ID 列表，帖子作者不能在此列表中"""

    author_name: Optional[str] = None
    """作者名称（模糊匹配），用于按作者名搜索"""

    tag_logic: str = "and"
    """标签逻辑，'and' 表示必须包含所有标签，'or' 表示包含任意标签"""

    sort_method: str = "comprehensive"
    """排序方法，可选值：'comprehensive'（综合排序）、'created_at'（创建时间）、
    'last_active_at'（最后活跃时间）、'reaction_count'（点赞数）、
    'reply_count'（回复数）、'collection_count'（收藏数）、'collected_at'（收藏时间）、
    'reddit_hot'（Reddit Hot 热门算法）、'custom'（自定义）"""

    sort_order: str = "desc"
    """排序顺序，'desc' 表示降序，'asc' 表示升序"""

    custom_base_sort: str = "comprehensive"
    """自定义排序的基础方法，当 sort_method='custom' 时使用此值"""

    reaction_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    """点赞数范围'"""

    reply_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    """回复数范围'"""

    created_after: Optional[str] = None
    """创建时间下限"""

    created_before: Optional[str] = None
    """创建时间上限"""

    active_after: Optional[str] = None
    """最后活跃时间下限，支持相对时间（如 '7d'、'1m'）或绝对时间（ISO 格式）"""

    active_before: Optional[str] = None
    """最后活跃时间上限，支持相对时间（如 '7d'、'1m'）或绝对时间（ISO 格式）"""

    user_id_for_collection_search: Optional[int] = None
    """用户 ID，用于搜索该用户的收藏帖子"""
