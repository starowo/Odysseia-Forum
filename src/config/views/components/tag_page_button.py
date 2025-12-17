from typing import Callable, Coroutine

import discord


class TagPageButton(discord.ui.Button):
    """一个用于标签选择视图翻页的自定义按钮。"""

    def __init__(
        self,
        action: str,
        callback_func: Callable[[discord.Interaction, str], Coroutine],
        row: int,
        disabled: bool = False,
    ):
        label = "◀️ 上一页" if action == "prev" else "▶️ 下一页"
        style = discord.ButtonStyle.secondary
        custom_id = f"tag_page_{action}"
        super().__init__(
            label=label, style=style, custom_id=custom_id, row=row, disabled=disabled
        )
        self.action = action
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.action)
