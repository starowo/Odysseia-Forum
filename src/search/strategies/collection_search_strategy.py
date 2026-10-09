import logging
from typing import TYPE_CHECKING, Awaitable, Callable, List, Optional

import discord

from search.constants import SortMethod
from search.search_service import SearchService
from search.strategies.search_strategy import SearchStrategy
from search.components.batch_collection_button import BatchCollectionButton
from search.components.keyword_modal import KeywordButton
from search.components.sort_method_select import SortMethodSelect
from search.components.sort_order_button import SortOrderButton
from search.components.tag_logic_button import TagLogicButton
from search.components.tag_page_button import TagPageButton
from shared.views.tag_select import TagSelect

if TYPE_CHECKING:
    from search.cog import Search
    from search.dto.search_state import SearchStateDTO
    from search.qo.thread_search import ThreadSearchQuery
    from search.views import GenericSearchView

logger = logging.getLogger(__name__)


class CollectionSearchStrategy(SearchStrategy):
    """用户收藏搜索策略"""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_title(self) -> str:
        return "收藏夹 : "

    async def get_available_tags(
        self, cog: "Search", state: "SearchStateDTO"
    ) -> List[str]:
        async with cog.session_factory() as session:
            service = SearchService(session, cog.tag_service)
            tags = await service.get_tags_for_collections(
                self.user_id, include_abyss=state.can_view_abyss_tags
            )
        # 使用 set 去除重复的标签名，然后排序
        return sorted(list(set(tag.name for tag in tags)))

    def modify_query(self, query: "ThreadSearchQuery") -> "ThreadSearchQuery":
        # 在这里注入用户ID，用于数据库JOIN
        query.user_id_for_collection_search = self.user_id
        return query

    def get_filter_components(self, view: "GenericSearchView") -> List[discord.ui.Item]:
        """准备所有筛选UI组件的列表"""
        components = []
        state = view.search_state
        all_tags = state.all_available_tags

        # 第 0 行: 批量操作按钮
        components.append(
            BatchCollectionButton(
                label="批量收藏",
                emoji="✨",
                callback_func=self.show_batch_collect_view,
                refresh_callback=view.refresh_view,
                row=0,
            )
        )
        components.append(
            BatchCollectionButton(
                label="批量取消收藏",
                emoji="🗑️",
                callback_func=self.show_batch_uncollect_view,
                refresh_callback=view.refresh_view,
                row=0,
            )
        )

        # 第 1 行: 正选标签
        components.append(
            TagSelect(
                all_tags=all_tags,
                selected_tags=state.include_tags,
                page=state.tag_page,
                tags_per_page=view.tags_per_page,
                placeholder_prefix="正选",
                custom_id="generic_include_tags",
                on_change_callback=view.on_include_tags_change,
                row=1,
            )
        )

        # 第 2 行: 控制按钮
        components.append(KeywordButton(view.show_keyword_modal, row=2))

        if len(all_tags) > view.tags_per_page:
            max_page = (len(all_tags) - 1) // view.tags_per_page
            components.append(
                TagPageButton(
                    "prev", view.on_tag_page_change, row=2, disabled=state.tag_page == 0
                )
            )

        components.append(
            TagLogicButton(state.tag_logic, view.on_tag_logic_change, row=2)
        )

        if len(all_tags) > view.tags_per_page:
            max_page = (len(all_tags) - 1) // view.tags_per_page
            components.append(
                TagPageButton(
                    "next",
                    view.on_tag_page_change,
                    row=2,
                    disabled=state.tag_page >= max_page,
                )
            )

        components.append(
            SortOrderButton(state.sort_order, view.on_sort_order_change, row=2)
        )

        # 第 3 行: 排序选择器
        sort_select = SortMethodSelect(
            state.sort_method, view.on_sort_method_change, row=3
        )

        # 动态修改自定义搜索的标签
        if state.sort_method == "custom":
            # 找到 "自定义搜索" 对应的选项
            custom_option = next(
                (opt for opt in sort_select.options if opt.value == "custom"), None
            )

            if custom_option:
                # 获取基础排序算法的显示名称
                base_sort_label = SortMethod.get_short_label_by_value(
                    state.custom_base_sort
                )

                # 更新标签
                custom_option.label = f"🛠️ 自定义 ({base_sort_label})"

        components.append(sort_select)

        return components

    async def show_batch_collect_view(
        self,
        interaction: discord.Interaction,
        refresh_callback: Callable[[], Awaitable[None]],
    ):
        """派发事件以显示批量收藏视图"""
        interaction.client.dispatch(
            "show_batch_collect_view", interaction, refresh_callback
        )

    async def show_batch_uncollect_view(
        self,
        interaction: discord.Interaction,
        refresh_callback: Callable[[], Awaitable[None]],
    ):
        """派发事件以显示批量取消收藏视图"""
        interaction.client.dispatch(
            "show_batch_uncollect_view", interaction, refresh_callback
        )

    def get_no_results_summary(self, has_filters: bool) -> Optional[str]:
        """如果策略有特殊的无结果提示，则返回提示信息"""
        if not has_filters:
            return "您还没有收藏帖子\n请点击想收藏的帖子中任意消息，在菜单中选择 APP -> 收藏此贴"
        return None
