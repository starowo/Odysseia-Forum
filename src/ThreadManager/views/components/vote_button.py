"""标签投票按钮组件。"""

from typing import Callable, Coroutine

import discord


class TagVoteButton(discord.ui.Button):
    """一个简单的标签投票按钮，将逻辑委托给视图。"""

    def __init__(
        self,
        tag_id: int,
        tag_name: str,
        vote_value: int,
        row: int,
        callback: Callable[["TagVoteButton", discord.Interaction], Coroutine],
    ):
        self.tag_id = tag_id
        self.tag_name = tag_name
        self.vote_value = vote_value
        self._callback = callback

        emoji = "👍" if vote_value == 1 else "👎"
        style = (
            discord.ButtonStyle.green if vote_value == 1 else discord.ButtonStyle.red
        )

        super().__init__(
            label=tag_name,
            emoji=emoji,
            style=style,
            row=row,
            custom_id=f"tag_vote:{tag_id}:{vote_value}",
        )

    async def callback(self, interaction: discord.Interaction):
        # 将交互和自身实例传递给视图中定义的实际回调逻辑
        await self._callback(self, interaction)
