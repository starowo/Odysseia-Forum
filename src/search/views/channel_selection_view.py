import discord
from typing import List, TYPE_CHECKING, Sequence

from shared.safe_defer import safe_defer
from .generic_search_view import GenericSearchView

if TYPE_CHECKING:
    from ..cog import Search
    from ..dto.search_state import SearchStateDTO


class ChannelSelectionView(discord.ui.View):
    """第一步：让用户选择要搜索的频道（支持多选）。"""

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

        preselected_ids = set(initial_state.channel_ids)

        # 构建选项
        options = [
            discord.SelectOption(
                label="所有已索引频道",
                value="all",
                default="all" in preselected_ids,
            )
        ]
        # Discord限制25个选项，为"all"选项留一个位置
        options.extend(
            [
                discord.SelectOption(
                    label=ch.name,
                    value=str(ch.id),
                    default=ch.id in preselected_ids,
                )
                for ch in channels[:24]
            ]
        )

        # 如果有预设值，确定按钮初始就可点击
        initial_disabled = not bool(preselected_ids)

        self.channel_select = discord.ui.Select(
            placeholder="选择论坛频道（可多选）...",
            options=options,
            min_values=1,
            max_values=len(options),
        )
        self.channel_select.callback = self.on_channel_select
        self.add_item(self.channel_select)

        self.confirm_button = discord.ui.Button(
            label="✅ 确定搜索",
            style=discord.ButtonStyle.success,
            disabled=initial_disabled,
        )
        self.confirm_button.callback = self.on_confirm
        self.add_item(self.confirm_button)

    async def on_channel_select(self, interaction: discord.Interaction):
        """当用户在下拉菜单中做出选择时调用。"""
        # 启用确定按钮
        self.confirm_button.disabled = False

        selected_values = self.channel_select.values

        # 更新选项的默认状态以保持选择
        for option in self.channel_select.options:
            option.default = option.value in selected_values

        # 更新消息以反映当前选择
        if "all" in selected_values:
            display_text = "所有已索引频道"
        else:
            # 从 self.channels 中查找名称
            selected_names = [
                ch.name for ch in self.channels if str(ch.id) in selected_values
            ]
            display_text = ", ".join(selected_names)

        await interaction.response.edit_message(
            content=f"**已选择:** {display_text}\n\n请点击“确定搜索”继续。", view=self
        )

    async def on_confirm(self, interaction: discord.Interaction):
        """当用户点击“确定”按钮后，切换到通用的搜索视图。"""
        await safe_defer(interaction)

        selected_values = self.channel_select.values
        selected_ids: List[int] = []

        if "all" in selected_values:
            # 如果选择了 "all"，则使用所有可用的频道ID
            selected_ids = list(self.all_channel_ids)
        elif selected_values:
            selected_ids = [int(v) for v in selected_values]
        else: # 如果用户清空了选择但点击了确定（可能是因为有预设值）
            selected_ids = self.search_state.channel_ids

        if not selected_ids:
            await interaction.followup.send("请至少选择一个频道。", ephemeral=True)
            return

        # 更新 search_state 中的频道列表
        self.search_state.channel_ids = selected_ids

        # 启动通用搜索视图，并传入更新后的状态
        generic_view = GenericSearchView(self.cog, interaction, self.search_state)
        await generic_view.start()
