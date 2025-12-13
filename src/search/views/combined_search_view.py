from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from search.views.generic_search_view import GenericSearchView
    from search.views.results_view import SearchResultsView


class CombinedSearchView(discord.ui.View):
    """
    一个组合视图，它将筛选视图 (GenericSearchView) 和
    结果分页视图 (SearchResultsView) 的组件合并在一起，并委托相应的逻辑。
    """

    def __init__(
        self,
        search_view: "GenericSearchView",
        results_view: "SearchResultsView",
        filter_components: list,
    ):
        # 超时时间继承自 search_view
        super().__init__(timeout=search_view.timeout)
        self.search_view = search_view
        self.results_view = results_view

        # 添加由 GenericSearchView 准备好的筛选组件
        for item in filter_components:
            self.add_item(item)

        # 添加 results_view (分页) 的所有组件，并强制设置行号为 4
        for item in self.results_view.children:
            item.row = 4
            self.add_item(item)

    async def on_timeout(self):
        """超时逻辑完全委托给 search_view 来处理，因为它持有所有状态。"""
        await self.search_view.on_timeout()
