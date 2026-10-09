import asyncio
from typing import TYPE_CHECKING, Optional

import discord

from search.dto.search_state import SearchStateDTO
from search.components.number_range_modal import NumberRangeModal
from search.components.sort_method_select import SortMethodSelect
from shared.enum import DefaultPreferences
from shared.safe_defer import safe_defer
from shared.views.components.time_range_modal import TimeRangeModal

if TYPE_CHECKING:
    from search.views.generic_search_view import GenericSearchView


class CustomSearchSettingsView(discord.ui.View):
    def __init__(self, parent_view: "GenericSearchView"):
        super().__init__(timeout=14400)  # 4 小时
        self.parent = parent_view
        self.state: SearchStateDTO = parent_view.search_state
        self.original_interaction: discord.Interaction = parent_view.last_interaction
        self.last_settings_interaction: Optional[discord.Interaction] = None
        self.update_components()

    def update_components(self):
        self.clear_items()
        self.add_item(
            discord.ui.Button(
                label="设置数值范围",
                style=discord.ButtonStyle.secondary,
                custom_id="set_num_range",
                row=0,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="设置时间范围",
                style=discord.ButtonStyle.secondary,
                custom_id="set_time_range",
                row=0,
            )
        )

        # 移除自定义选项本身，只保留基础排序
        base_sort_select = SortMethodSelect(
            self.state.custom_base_sort, self.on_base_sort_change, row=1
        )
        base_sort_select.options = [
            opt for opt in base_sort_select.options if opt.value != "custom"
        ]
        self.add_item(base_sort_select)
        self.add_item(
            discord.ui.Button(
                label="🗑️ 清空范围设置",
                style=discord.ButtonStyle.danger,
                custom_id="clear_ranges",
                row=2,
            )
        )
        # 绑定回调
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.callback = self.button_callback

    def build_embed(self):
        embed = discord.Embed(
            title="🛠️ 自定义搜索设置",
            description="以选择的排序算法作为基础，并应用更精细的筛选条件",
            color=discord.Color.blue(),
        )

        # 数值范围
        reaction_display = (
            f"{self.state.reaction_count_range}"
            if self.state.reaction_count_range
            != DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            else "未设置"
        )

        reply_display = (
            f"{self.state.reply_count_range}"
            if self.state.reply_count_range
            != DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            else "未设置"
        )

        num_range_value = f"反应数: {reaction_display}\n回复数: {reply_display}"
        embed.add_field(name="🔢 数值范围", value=num_range_value, inline=False)

        # 时间范围
        time_range_parts = []
        if self.state.created_after:
            time_range_parts.append(f"发帖晚于: {self.state.created_after}")
        if self.state.created_before:
            time_range_parts.append(f"发帖早于: {self.state.created_before}")
        if self.state.active_after:
            time_range_parts.append(f"活跃晚于: {self.state.active_after}")
        if self.state.active_before:
            time_range_parts.append(f"活跃早于: {self.state.active_before}")

        time_range_value = "\n".join(time_range_parts) if time_range_parts else "未设置"
        embed.add_field(name="📅 时间范围", value=time_range_value, inline=False)

        return embed

    async def start(self) -> Optional[discord.WebhookMessage]:
        """发送配置视图并返回消息对象"""
        return await self.original_interaction.followup.send(
            embed=self.build_embed(), view=self, ephemeral=True, wait=True
        )

    async def button_callback(self, interaction: discord.Interaction):
        if not interaction.data:
            await safe_defer(interaction)
            return

        # 保存本次交互，以便在模态框提交后用它来更新本视图
        self.last_settings_interaction = interaction

        custom_id = interaction.data.get("custom_id")

        if custom_id == "clear_ranges":
            # 清空所有数值和时间范围设置
            self.state.reaction_count_range = (
                DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            )
            self.state.reply_count_range = (
                DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
            )
            self.state.created_after = None
            self.state.created_before = None
            self.state.active_after = None
            self.state.active_before = None

            await safe_defer(interaction)

            # 创建一个后台任务去执行父视图的搜索
            asyncio.create_task(
                self.parent.trigger_search_from_custom_settings(self.state)
            )

            # 使用当前交互来更新本视图的消息
            self.update_components()
            await interaction.edit_original_response(
                embed=self.build_embed(), view=self
            )
            return

        if custom_id == "set_num_range":
            await interaction.response.send_modal(
                NumberRangeModal(self.state, self.handle_num_modal_submit)
            )
        elif custom_id == "set_time_range":
            initial_values = {
                "created_after": self.state.created_after,
                "created_before": self.state.created_before,
                "active_after": self.state.active_after,
                "active_before": self.state.active_before,
            }
            modal = TimeRangeModal(self.handle_time_modal_submit, initial_values)
            await interaction.response.send_modal(modal)

    async def on_base_sort_change(
        self, interaction: discord.Interaction, new_method: str
    ):
        self.state.custom_base_sort = new_method

        # 响应下拉菜单的交互
        await safe_defer(interaction)

        # 创建后台任务去执行父视图的搜索
        asyncio.create_task(self.parent.trigger_search_from_custom_settings(self.state))

        # 更新本视图的 embed 和 view
        self.update_components()
        await interaction.edit_original_response(embed=self.build_embed(), view=self)

    async def handle_num_modal_submit(self, values: dict):
        """处理来自 NumberRangeModal 的数据"""
        self.state.reaction_count_range = values.get(
            "reaction_count_range", DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
        )
        self.state.reply_count_range = values.get(
            "reply_count_range", DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
        )

        # 创建一个后台任务去执行父视图的搜索
        asyncio.create_task(self.parent.trigger_search_from_custom_settings(self.state))

        # 使用点击按钮时保存的交互来更新本视图的消息
        self.update_components()
        if self.last_settings_interaction:
            await self.last_settings_interaction.edit_original_response(
                embed=self.build_embed(), view=self
            )

    async def on_timeout(self):
        """
        视图超时后，清理程序内存状态。
        由于是私密消息，此时交互 Token 已失效，无法通过 API 删除它。
        """
        if self.parent:
            self.parent.custom_settings_message = None
        self.last_settings_interaction = None

    async def handle_time_modal_submit(
        self, interaction: discord.Interaction, values: dict
    ):
        """回调：接收字符串，更新state，并触发搜索"""
        self.state.created_after = values.get("created_after")
        self.state.created_before = values.get("created_before")
        self.state.active_after = values.get("active_after")
        self.state.active_before = values.get("active_before")

        # 创建一个后台任务去执行父视图的搜索
        asyncio.create_task(self.parent.trigger_search_from_custom_settings(self.state))

        # 使用点击按钮时保存的交互来更新本视图的消息
        self.update_components()
        if self.last_settings_interaction:
            await self.last_settings_interaction.edit_original_response(
                embed=self.build_embed(), view=self
            )
