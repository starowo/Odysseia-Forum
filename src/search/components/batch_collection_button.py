from typing import Awaitable, Callable

import discord


class BatchCollectionButton(discord.ui.Button):
    """用于触发批量收藏/取消收藏视图的按钮"""

    def __init__(
        self,
        label: str,
        emoji: str,
        callback_func,
        refresh_callback: Callable[[], Awaitable[None]],
        row: int,
    ):
        super().__init__(
            label=label, emoji=emoji, style=discord.ButtonStyle.secondary, row=row
        )
        self.callback_func = callback_func
        self.refresh_callback = refresh_callback

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.callback_func(interaction, self.refresh_callback)
