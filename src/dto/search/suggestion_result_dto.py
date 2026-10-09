from dataclasses import dataclass, field
from typing import List

from models import Author, Booklist, Thread, Tag


@dataclass
class SuggestionResultDTO:
    """搜索联想建议的聚合结果"""

    authors: List[Author] = field(default_factory=list)
    threads: List[Thread] = field(default_factory=list)
    booklists: List[Booklist] = field(default_factory=list)

    tags: List[Tag] = field(default_factory=list)
    """按标准名或别名匹配的可用标签实体"""
