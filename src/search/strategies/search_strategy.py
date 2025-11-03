import abc
import discord
from typing import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..cog import Search
    from ..qo.thread_search import ThreadSearchQuery
    from ..dto.search_state import SearchStateDTO
    from ..views.generic_search_view import GenericSearchView


class SearchStrategy(abc.ABC):
    """搜索策略的抽象基类"""

    @abc.abstractmethod
    def get_title(self) -> str:
        """获取搜索视图的标题"""
        pass

    @abc.abstractmethod
    async def get_available_tags(
        self, cog: "Search", state: "SearchStateDTO"
    ) -> List[str]:
        """根据当前策略获取所有可用的标签名称列表"""
        pass

    @abc.abstractmethod
    def modify_query(self, query: "ThreadSearchQuery") -> "ThreadSearchQuery":
        """在执行搜索前，根据策略修改查询对象"""
        pass

    @abc.abstractmethod
    def get_filter_components(self, view: "GenericSearchView") -> List[discord.ui.Item]:
        """准备所有筛选UI组件的列表"""
        pass

    @abc.abstractmethod
    def get_no_results_summary(self, has_filters: bool) -> Optional[str]:
        """如果策略有特殊的无结果提示，则返回提示信息"""
        pass
