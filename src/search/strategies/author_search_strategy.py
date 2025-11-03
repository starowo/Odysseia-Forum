import discord
from typing import List, TYPE_CHECKING, Optional
from .search_strategy import SearchStrategy
from shared.views.tag_select import TagSelect
from ..views.components.keyword_modal import KeywordButton
from ..views.components.tag_logic_button import TagLogicButton
from ..views.components.sort_order_button import SortOrderButton
from ..views.components.sort_method_select import SortMethodSelect
from ..views.components.tag_page_button import TagPageButton
from ..constants import SortMethod

if TYPE_CHECKING:
    from ..cog import Search
    from ..qo.thread_search import ThreadSearchQuery
    from ..dto.search_state import SearchStateDTO
    from ..views.generic_search_view import GenericSearchView


class AuthorSearchStrategy(SearchStrategy):
    """作者搜索策略"""

    def __init__(self, author_id: int):
        self.author_id = author_id

    def get_title(self) -> str:
        return "搜索结果 : "

    async def get_available_tags(
        self, cog: "Search", state: "SearchStateDTO"
    ) -> List[str]:
        """从数据库获取该作者使用过的所有标签"""
        tags = await cog.get_tags_for_author(self.author_id)
        return sorted([tag.name for tag in tags])

    def modify_query(self, query: "ThreadSearchQuery") -> "ThreadSearchQuery":
        # 作者 ID 已经在入口点处被强制设置到 SearchStateDTO.include_authors 中，
        # 因此，此策略在修改查询阶段无需做额外操作。
        return query

    def get_filter_components(self, view: "GenericSearchView") -> List[discord.ui.Item]:
        """准备所有筛选UI组件的列表"""
        components = []
        state = view.search_state
        all_tags = state.all_available_tags

        # 第 0 行: 正选标签
        components.append(
            TagSelect(
                all_tags=all_tags,
                selected_tags=state.include_tags,
                page=state.tag_page,
                tags_per_page=view.tags_per_page,
                placeholder_prefix="正选",
                custom_id="generic_include_tags",
                on_change_callback=view.on_include_tags_change,
                row=0,
            )
        )

        # 第 1 行: 反选标签
        components.append(
            TagSelect(
                all_tags=all_tags,
                selected_tags=state.exclude_tags,
                page=state.tag_page,
                tags_per_page=view.tags_per_page,
                placeholder_prefix="反选",
                custom_id="generic_exclude_tags",
                on_change_callback=view.on_exclude_tags_change,
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

    def get_no_results_summary(self, has_filters: bool) -> Optional[str]:
        """如果策略有特殊的无结果提示，则返回提示信息"""
        return None
