import discord
from typing import TYPE_CHECKING

from .components.continue_button import ContinueButton

if TYPE_CHECKING:
    from ..cog import Search


class TimeoutView(discord.ui.View):
    """一个简单的视图，只包含一个“继续”按钮。"""

    def __init__(
        self, cog: "Search", original_interaction: discord.Interaction, state: dict
    ):
        super().__init__(timeout=None)  # TimeoutView 本身不应该超时
        self.add_item(ContinueButton(cog, original_interaction, state))
