from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from search.qo.thread_search import ThreadSearchQuery


@dataclass
class CleanedThreadSearchQuery:
    """清洗后的搜索查询数据，所有字段均已规范化"""

    # 原始查询引用（保留未清洗的字段供后续使用）
    query: ThreadSearchQuery

    # 解析后的时间
    created_after_dt: Optional[datetime] = None
    created_before_dt: Optional[datetime] = None
    active_after_dt: Optional[datetime] = None
    active_before_dt: Optional[datetime] = None

    # 解析后的标签 ID
    resolved_include_tag_ids: List[int] = field(default_factory=list)
    resolved_exclude_tag_ids: List[int] = field(default_factory=list)

    # 规范化后的排除帖子 ID
    normalized_exclude_thread_ids: List[int] = field(default_factory=list)

    # 规范化后的包含作者 ID（已转为 set）
    final_include_author_ids: set[int] = field(default_factory=set)

    # 规范化后的作者名
    normalized_author_name: Optional[str] = None
