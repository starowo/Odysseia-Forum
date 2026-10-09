import math
from typing import TYPE_CHECKING

import discord

from search.qo.thread_search import ThreadSearchQuery
from shared.views.components.page_jump_modal import PageJumpModal

if TYPE_CHECKING:
    from search.cog import Search


class SearchResultsView(discord.ui.View):
    def __init__(
        self,
        cog: "Search",
        interaction: discord.Interaction,
        search_qo: "ThreadSearchQuery",
        total: int,
        page: int,
        per_page: int,
        page_callback,
        results_per_page: int,
        preview_image_mode: str,
    ):
        super().__init__(timeout=14400)
        self.cog = cog
        self.interaction = interaction
        self.search_qo = search_qo
        self.total = total
        self.page = page
        self.per_page = per_page
        self.max_page = max(1, math.ceil(total / per_page))
        self.page_callback = page_callback
        self.results_per_page = results_per_page
        self.preview_image_mode = preview_image_mode

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()

        first_page = discord.ui.Button(
            label="⏮️", style=discord.ButtonStyle.secondary, disabled=(self.page == 1)
        )
        first_page.callback = self.go_to_first_page
        self.add_item(first_page)

        prev_page = discord.ui.Button(
            label="◀️", style=discord.ButtonStyle.secondary, disabled=(self.page == 1)
        )
        prev_page.callback = self.go_to_previous_page
        self.add_item(prev_page)

        current_page_button = discord.ui.Button(
            label=f"{self.page}/{self.max_page}",
            style=discord.ButtonStyle.primary,
            disabled=False,
        )
        current_page_button.callback = self.show_page_jump_modal
        self.add_item(current_page_button)

        next_page = discord.ui.Button(
            label="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page == self.max_page),
        )
        next_page.callback = self.go_to_next_page
        self.add_item(next_page)

        last_page = discord.ui.Button(
            label="⏭️",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page == self.max_page),
        )
        last_page.callback = self.go_to_last_page
        self.add_item(last_page)

    async def show_page_jump_modal(self, interaction: discord.Interaction):
        """显示用于跳转页面的模态框"""
        modal = PageJumpModal(max_page=self.max_page, submit_callback=self.go_to_page)
        await interaction.response.send_modal(modal)

    async def go_to_page(self, interaction: discord.Interaction, page: int):
        # 调用从 GenericSearchView 传入的回调函数
        if self.page_callback:
            await self.page_callback(
                interaction,
                page=page,
                per_page=self.results_per_page,
                preview_mode=self.preview_image_mode,
            )

    async def go_to_first_page(self, interaction: discord.Interaction):
        await self.go_to_page(interaction, 1)

    async def go_to_previous_page(self, interaction: discord.Interaction):
        await self.go_to_page(interaction, self.page - 1)

    async def go_to_next_page(self, interaction: discord.Interaction):
        await self.go_to_page(interaction, self.page + 1)

    async def go_to_last_page(self, interaction: discord.Interaction):
        await self.go_to_page(interaction, self.max_page)

    async def on_timeout(self):
        """分页视图超时，私密消息的 Token 已失效，放弃任何 API 编辑请求。"""
        pass
