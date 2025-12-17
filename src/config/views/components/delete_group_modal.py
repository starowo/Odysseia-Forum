from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from config.mutex_tags_handler import MutexTagsHandler
    from config.views.mutex_config_view import MutexConfigView


class DeleteGroupModal(discord.ui.Modal, title="删除互斥组"):
    def __init__(self, handler: "MutexTagsHandler", view: "MutexConfigView"):
        super().__init__()
        self.handler = handler
        self.view = view
        self.group_id_input = discord.ui.TextInput(
            label="输入要删除的互斥组ID", placeholder="例如: 1"
        )
        self.add_item(self.group_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.handler.process_delete_modal(
            interaction, self.group_id_input.value, self.view
        )
