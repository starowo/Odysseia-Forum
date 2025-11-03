import discord
from typing import TYPE_CHECKING, Type

from ...dto.search_state import SearchStateDTO
from ...strategies import (
    DefaultSearchStrategy,
    AuthorSearchStrategy,
    CollectionSearchStrategy,
)

if TYPE_CHECKING:
    from ...cog import Search
    from ..generic_search_view import GenericSearchView


class ContinueButton(discord.ui.Button):
    """用于从超时状态恢复视图的按钮。"""

    def __init__(
        self,
        cog: "Search",
        original_interaction: discord.Interaction,
        state: dict,
        view_class: Type["GenericSearchView"],
    ):
        super().__init__(label="🔄 继续搜索", style=discord.ButtonStyle.primary)
        self.cog = cog
        self.original_interaction = original_interaction
        self.state = state
        self.view_class = view_class

    async def callback(self, interaction: discord.Interaction):
        # 从 state 字典重建 SearchStateDTO
        search_state = SearchStateDTO(**self.state)

        # 根据保存的策略信息重新创建策略对象
        strategy = self._recreate_strategy(search_state)

        # 使用注入的类创建新的 GenericSearchView 实例
        view = self.view_class(
            cog=self.cog,
            interaction=interaction,
            search_state=search_state,
            strategy=strategy,
        )

        # 使用恢复的状态更新视图。
        await view.update_view(interaction, rerun_search=True)

    def _recreate_strategy(self, search_state: SearchStateDTO):
        """根据保存的策略信息重新创建策略对象"""
        strategy_type = search_state.strategy_type
        strategy_params = search_state.strategy_params or {}

        if strategy_type == "author":
            author_id = strategy_params.get("author_id")
            if author_id is not None:
                return AuthorSearchStrategy(author_id=int(author_id))
            else:
                # 如果参数缺失，回退到默认策略
                return DefaultSearchStrategy()
        elif strategy_type == "collection":
            user_id = strategy_params.get("user_id")
            if user_id is not None:
                return CollectionSearchStrategy(user_id=int(user_id))
            else:
                # 如果参数缺失，回退到默认策略
                return DefaultSearchStrategy()
        else:  # default
            return DefaultSearchStrategy()
