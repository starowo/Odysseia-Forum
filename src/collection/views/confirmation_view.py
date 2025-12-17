from typing import Callable, Coroutine

import discord


class ConfirmButton(discord.ui.Button):
    """一个通用的确认按钮，执行传入的回调函数"""

    def __init__(
        self,
        label: str,
        style: discord.ButtonStyle,
        custom_id: str,
        callback: Callable[[discord.Interaction, discord.ui.Button], Coroutine],
    ):
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.callback_func = callback

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self)


class ConfirmationView(discord.ui.View):
    """一个通用的二次确认视图，包含确认和取消按钮"""

    def __init__(
        self,
        confirm_callback: Callable[[discord.Interaction, discord.ui.Button], Coroutine],
    ):
        super().__init__(timeout=300)
        self.add_item(
            ConfirmButton(
                "确认", discord.ButtonStyle.danger, "confirm", confirm_callback
            )
        )
        self.add_item(
            ConfirmButton("取消", discord.ButtonStyle.secondary, "cancel", self.cancel)
        )

    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """取消操作，并编辑消息提示用户"""
        await interaction.response.edit_message(
            content="操作已取消。", view=None, delete_after=60
        )

    async def on_timeout(self):
        """视图超时后禁用所有按钮"""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
