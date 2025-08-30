import discord
from typing import Callable, Coroutine

from shared.safe_defer import safe_defer


class PageJumpModal(discord.ui.Modal, title="跳转到页面"):
    def __init__(
        self,
        max_page: int,
        submit_callback: Callable[[discord.Interaction, int], Coroutine],
    ):
        super().__init__()
        self.max_page = max_page
        self.submit_callback = submit_callback
        self.page_input = discord.ui.TextInput(
            label=f"输入页码 (1-{self.max_page})",
            placeholder=f"请输入 1 到 {self.max_page} 之间的数字",
            required=True,
            min_length=1,
            max_length=len(str(self.max_page)),
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            page_num = int(self.page_input.value)
            if 1 <= page_num <= self.max_page:
                await self.submit_callback(interaction, page_num)
            else:
                await interaction.followup.send(
                    f"页码必须在 1 到 {self.max_page} 之间。", ephemeral=True
                )
        except ValueError:
            await interaction.followup.send("请输入一个有效的数字。", ephemeral=True)
