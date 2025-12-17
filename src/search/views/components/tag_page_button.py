from typing import Callable, Coroutine, Literal

import discord


class TagPageButton(discord.ui.Button):
    """一个用于标签分页的按钮组件。"""

    def __init__(
        self,
        action: Literal["prev", "next"],
        callback: Callable[[discord.Interaction, Literal["prev", "next"]], Coroutine],
        **kwargs,
    ):
        label = "◀️ 上一页" if action == "prev" else "▶️ 下一页"
        super().__init__(label=label, style=discord.ButtonStyle.secondary, **kwargs)
        self.action = action
        self._callback_func = callback

    async def callback(self, interaction: discord.Interaction):
        """按钮被点击时，调用父视图注册的回调函数。"""
        await self._callback_func(interaction, self.action)
