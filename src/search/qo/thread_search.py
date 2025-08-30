from dataclasses import dataclass, field
from typing import Optional, List
import datetime


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
    after_ts: Optional[datetime.datetime] = None
    before_ts: Optional[datetime.datetime] = None
    tag_logic: str = "and"
    sort_method: str = "comprehensive"
    sort_order: str = "desc"
