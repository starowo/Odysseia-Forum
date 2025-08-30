import discord
from typing import List, Callable, Awaitable


class AuthorSelect(discord.ui.UserSelect):
    """一个独立的作者选择下拉菜单组件。"""

    def __init__(
        self,
        callback: Callable[[discord.Interaction, List[discord.User]], Awaitable[None]],
        row: int,
    ):
        super().__init__(placeholder="筛选作者", min_values=0, max_values=25, row=row)
        self.select_callback = callback

    async def callback(self, interaction: discord.Interaction):
        await self.select_callback(interaction, self.values)
