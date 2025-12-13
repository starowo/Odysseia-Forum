from typing import TYPE_CHECKING, Sequence, Set

import discord

from search.strategies import DefaultSearchStrategy
from shared.safe_defer import safe_defer
from search.views.generic_search_view import GenericSearchView

if TYPE_CHECKING:
    from search.cog import Search
    from search.dto.search_state import SearchStateDTO


class ChannelSelectionView(discord.ui.View):
    """
    让用户选择要搜索的频道
    若用户未选择任何频道，则默认搜索所有已索引频道。
    """

    def __init__(
        self,
        cog: "Search",
        original_interaction: discord.Interaction,
        channels: Sequence[discord.ForumChannel],
        all_channel_ids: Sequence[int],
        initial_state: "SearchStateDTO",
    ):
        super().__init__(timeout=900)
        self.cog = cog
        self.original_interaction = original_interaction
        self.channels = channels
        self.all_channel_ids = all_channel_ids
        self.search_state = initial_state

        # 使用集合来存储所有已选中的频道ID，支持跨页选择
        self.selected_channel_ids: Set[int] = set(initial_state.channel_ids)
        self.page = 0
        self.channels_per_page = 25

        # 初始化界面组件
        self.update_components()

    def update_components(self):
        """根据当前页面和选中状态，重新构建所有UI组件"""
        self.clear_items()

        # --- 计算分页 ---
        start_idx = self.page * self.channels_per_page
        end_idx = start_idx + self.channels_per_page
        current_page_channels = self.channels[start_idx:end_idx]
        total_pages = (len(self.channels) - 1) // self.channels_per_page

        # --- 构建下拉框选项 ---
        options = []
        for ch in current_page_channels:
            options.append(
                discord.SelectOption(
                    label=ch.name,
                    value=str(ch.id),
                    default=ch.id in self.selected_channel_ids,
                )
            )

        # 处理空选项的情况
        if not options:
            options.append(
                discord.SelectOption(label="无可用频道", value="none", default=False)
            )

        # --- 创建并添加下拉框 ---
        # 动态设置 placeholder 显示当前页信息
        placeholder = f"选择论坛频道 (第 {self.page + 1}/{total_pages + 1} 页)..."
        self.channel_select = discord.ui.Select(
            placeholder=placeholder,
            options=options,
            min_values=0,
            max_values=len(options),
            row=0,
            disabled=(options[0].value == "none"),
        )
        self.channel_select.callback = self.on_channel_select
        self.add_item(self.channel_select)

        # --- 添加分页按钮 (如果需要) ---
        if total_pages > 0:
            prev_btn = discord.ui.Button(
                label="◀️ 上一页",
                style=discord.ButtonStyle.secondary,
                row=1,
                disabled=(self.page <= 0),
            )
            prev_btn.callback = self.on_prev_page
            self.add_item(prev_btn)

            next_btn = discord.ui.Button(
                label="▶️ 下一页",
                style=discord.ButtonStyle.secondary,
                row=1,
                disabled=(self.page >= total_pages),
            )
            next_btn.callback = self.on_next_page
            self.add_item(next_btn)

        # --- 添加功能按钮 (确定/清空) ---
        self.confirm_button = discord.ui.Button(
            label="✅ 确定搜索",
            style=discord.ButtonStyle.success,
            row=2,
        )
        self.confirm_button.callback = self.on_confirm
        self.add_item(self.confirm_button)

        self.clear_button = discord.ui.Button(
            label="🧹 清空选择",
            style=discord.ButtonStyle.secondary,
            row=2,
            disabled=not bool(self.selected_channel_ids),
        )
        self.clear_button.callback = self.on_clear_selection
        self.add_item(self.clear_button)

    def build_embed(self) -> discord.Embed:
        """构建当前状态的提示 Embed"""
        selected_count = len(self.selected_channel_ids)

        if selected_count == 0:
            description = (
                "**当前未选择任何频道，将默认搜索所有频道**\n\n"
                "您可以从下方选择频道进行指定搜索\n"
            )
        else:
            # 获取已选频道的名称列表用于展示
            selected_names = [
                ch.name for ch in self.channels if ch.id in self.selected_channel_ids
            ]
            # 如果选中太多，只显示前几个
            display_names = selected_names[:10]
            if len(selected_names) > 10:
                display_names.append(f"...等共 {selected_count} 个频道")

            names_str = ", ".join(display_names)

            description = (
                f"**已选择 {selected_count} 个频道:**\n{names_str}\n\n"
                "点击“**确定搜索**”继续，或点击“**清空选择**”重置为搜索全部"
            )

        embed = discord.Embed(
            title="🔍 选择搜索频道",
            description=description,
            color=discord.Color.blue()
            if selected_count > 0
            else discord.Color.greyple(),
        )

        return embed

    async def refresh_view(self, interaction: discord.Interaction):
        """刷新消息视图"""
        self.update_components()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_channel_select(self, interaction: discord.Interaction):
        """处理下拉框选择变化"""
        # 找出当前页面显示的所有频道ID
        start_idx = self.page * self.channels_per_page
        end_idx = start_idx + self.channels_per_page
        current_page_ids = {ch.id for ch in self.channels[start_idx:end_idx]}

        # 从 master set 中移除当前页面的所有ID (先清空当前页的旧状态)
        self.selected_channel_ids -= current_page_ids

        # 将当前下拉框选中的ID添加回 master set
        new_selected_ids = {
            int(val) for val in self.channel_select.values if val != "none"
        }
        self.selected_channel_ids.update(new_selected_ids)

        await self.refresh_view(interaction)

    async def on_prev_page(self, interaction: discord.Interaction):
        """上一页"""
        self.page = max(0, self.page - 1)
        await self.refresh_view(interaction)

    async def on_next_page(self, interaction: discord.Interaction):
        """下一页"""
        max_page = (len(self.channels) - 1) // self.channels_per_page
        self.page = min(max_page, self.page + 1)
        await self.refresh_view(interaction)

    async def on_clear_selection(self, interaction: discord.Interaction):
        """清空所有选择"""
        self.selected_channel_ids.clear()
        await self.refresh_view(interaction)

    async def on_confirm(self, interaction: discord.Interaction):
        """确认选择并进入下一步"""
        await safe_defer(interaction, ephemeral=True)

        # 如果用户什么都没选，意味着"搜索全部"
        final_selected_ids = list(self.selected_channel_ids)
        if not final_selected_ids:
            final_selected_ids = []

        # 重新获取合并后的标签（基于最终选择的频道）
        merged_tag_names = self.cog.get_merged_tag_names(final_selected_ids)
        merged_tag_names_set = set(merged_tag_names)

        # 过滤已有偏好中的标签，确保它们在当前选定的频道中依然有效
        self.search_state.include_tags = self.search_state.include_tags.intersection(
            merged_tag_names_set
        )
        self.search_state.exclude_tags = self.search_state.exclude_tags.intersection(
            merged_tag_names_set
        )

        # 更新状态
        self.search_state.channel_ids = final_selected_ids
        self.search_state.all_available_tags = merged_tag_names

        

        generic_view = GenericSearchView(
            self.cog, interaction, self.search_state, strategy=DefaultSearchStrategy()
        )
        await generic_view.start()
