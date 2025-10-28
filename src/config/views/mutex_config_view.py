import logging
import discord
from typing import List, TYPE_CHECKING

from shared.safe_defer import safe_defer
from config.views.add_mutex_group_view import AddMutexGroupView

if TYPE_CHECKING:
    from config.mutex_tags_handler import MutexTagsHandler

logger = logging.getLogger(__name__)


# --- 主配置视图 ---
class MutexConfigView(discord.ui.View):
    def __init__(
        self,
        handler: "MutexTagsHandler",
        all_tag_names: List[str],
        origin_interaction: discord.Interaction,
    ):
        super().__init__(timeout=600)
        self.handler = handler
        self.all_tag_names = sorted(all_tag_names)
        self.origin_interaction: discord.Interaction = origin_interaction

        self.update_components()

    def update_components(self):
        self.clear_items()

        add_button = discord.ui.Button(
            label="➕ 新增", style=discord.ButtonStyle.primary
        )
        add_button.callback = self.on_add_button_click
        self.add_item(add_button)

        delete_button = discord.ui.Button(
            label="➖ 删除", style=discord.ButtonStyle.danger
        )
        delete_button.callback = self.on_delete_button_click
        self.add_item(delete_button)

        close_button = discord.ui.Button(
            label="🔒 关闭", style=discord.ButtonStyle.secondary
        )
        close_button.callback = self.on_close_button_click
        self.add_item(close_button)

    # --- 按钮回调 ---
    async def on_add_button_click(self, interaction: discord.Interaction):
        """点击新增按钮时，发送一个新的私密消息来显示新增设置视图"""
        await self.handler.handle_add_group_start(interaction, self.origin_interaction)

    async def on_delete_button_click(self, interaction: discord.Interaction):
        await self.handler.handle_delete_group(interaction, self)

    async def on_close_button_click(self, interaction: discord.Interaction):
        """点击关闭按钮时，删除消息"""
        await safe_defer(interaction)

        # 删除当前视图
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.delete_original_response(),
            priority=1,
        )
