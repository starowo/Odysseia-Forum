from typing import TYPE_CHECKING, Type

import discord

from search.views.components.continue_button import ContinueButton

if TYPE_CHECKING:
    from search.cog import Search
    from search.views.generic_search_view import GenericSearchView


class TimeoutView(discord.ui.View):
    """一个简单的视图，只包含一个“继续”按钮。"""

    def __init__(
        self,
        cog: "Search",
        original_interaction: discord.Interaction,
        state: dict,
        view_class: Type["GenericSearchView"],
    ):
        super().__init__(timeout=None)  # TimeoutView 本身不应该超时
        self.add_item(
            ContinueButton(
                cog=cog,
                original_interaction=original_interaction,
                state=state,
                view_class=view_class,
            )
        )
