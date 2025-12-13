from typing import TYPE_CHECKING, cast

import discord
from discord.ui import Label

from shared.enum.default_preferences import DefaultPreferences
from shared.range_parser import InvalidRangeFormat, parse_range_string
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from search.dto.search_state import SearchStateDTO


class NumberRangeModal(discord.ui.Modal, title="设置数值范围 (使用数学区间表示法)"):
    def __init__(self, current_state: "SearchStateDTO", callback):
        super().__init__(timeout=840)
        self.callback = callback

        default_range = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
        reaction_default = (
            default_range
            if current_state.reaction_count_range == default_range
            else current_state.reaction_count_range
        )

        reaction_input = discord.ui.TextInput(
            default=reaction_default,
            required=False,
        )

        # 使用 Label 组件进行说明
        self.add_item(
            discord.ui.Label(
                text="反应数范围",
                description=("数学区间表示法 :  \n\n[ ] 包含边界值, ( ) 不含边界值"),
                component=reaction_input,
            )
        )

        reply_default = (
            default_range
            if current_state.reply_count_range == default_range
            else current_state.reply_count_range
        )
        reply_input = discord.ui.TextInput(
            default=reply_default,
            required=False,
        )

        self.add_item(
            discord.ui.Label(
                text="回复数范围",
                description=(
                    "示例 : [10, 100) 表示 ≥10 且 <100 , (20, 50] 表示 >20 且 ≤50"
                ),
                component=reply_input,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        # 从 Label 的 .component 属性获取 TextInput
        reaction_label_item = cast(Label, self.children[0])
        reaction_range_input = cast(discord.ui.TextInput, reaction_label_item.component)
        reply_label_item = cast(Label, self.children[1])
        reply_range_input = cast(discord.ui.TextInput, reply_label_item.component)

        reaction_value = (
            reaction_range_input.value or DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
        )
        reply_value = (
            reply_range_input.value or DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
        )

        try:
            if reaction_range_input.value:
                parse_range_string(reaction_value)

            if reply_range_input.value:
                parse_range_string(reply_value)

        except InvalidRangeFormat as e:
            await interaction.response.send_message(
                f"❌ 输入有误：{e}", ephemeral=True, delete_after=120
            )
            return

        values = {
            "reaction_count_range": reaction_value,
            "reply_count_range": reply_value,
        }

        await safe_defer(interaction)

        # 将处理好的数据传递给回调函数
        await self.callback(values)
