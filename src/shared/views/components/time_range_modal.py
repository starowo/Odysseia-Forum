from typing import Callable, Coroutine, Dict, Optional, cast

import discord
from discord.ui import Label

from shared.safe_defer import safe_defer
from shared.time_parser import parse_time_string


class TimeRangeModal(discord.ui.Modal, title="设置时间范围"):
    def __init__(
        self,
        submit_callback: Callable[
            [discord.Interaction, Dict[str, Optional[str]]], Coroutine
        ],
        initial_values: Dict[str, Optional[str]],
    ):
        super().__init__(timeout=800)
        self.submit_callback = submit_callback

        # 提示用户可以使用相对时间
        placeholder_text = "格式: YYYY-MM-DD 或相对时间 (如 -3 d)"

        # 发帖时间输入框
        created_after_input = discord.ui.TextInput(
            default=initial_values.get("created_after"),
            placeholder=placeholder_text,
            required=False,
        )

        self.add_item(
            Label(
                text="发帖时间 (晚于)",
                description=("绝对时间示例 : \n\n2001-01-02"),
                component=created_after_input,
            )
        )

        created_before_input = discord.ui.TextInput(
            default=initial_values.get("created_before"),
            placeholder=placeholder_text,
            required=False,
        )

        self.add_item(
            Label(
                text="发帖时间 (早于)",
                description=(
                    "相对时间示例 : \n\n-3 day/week/month , -5d/w/m , 7 天/周/月前"
                ),
                component=created_before_input,
            )
        )

        # 活跃时间输入框
        self.add_item(
            discord.ui.TextInput(
                label="活跃时间 (晚于)",
                default=initial_values.get("active_after"),
                placeholder=placeholder_text,
                required=False,
            )
        )
        self.add_item(
            discord.ui.TextInput(
                label="活跃时间 (早于)",
                default=initial_values.get("active_before"),
                placeholder=placeholder_text,
                required=False,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        # 收集所有输入框的原始字符串值
        created_after_label = cast(Label, self.children[0])
        created_after_input = cast(discord.ui.TextInput, created_after_label.component)
        created_before_label = cast(Label, self.children[1])
        created_before_input = cast(
            discord.ui.TextInput, created_before_label.component
        )
        active_after_input = cast(discord.ui.TextInput, self.children[2])
        active_before_input = cast(discord.ui.TextInput, self.children[3])

        raw_values = {
            "created_after": created_after_input.value or None,
            "created_before": created_before_input.value or None,
            "active_after": active_after_input.value or None,
            "active_before": active_before_input.value or None,
        }

        try:
            # 验证所有非空输入的格式是否正确
            for value in raw_values.values():
                if value:
                    parse_time_string(value)
        except ValueError as e:
            # 如果任何一个格式错误，就向用户报错
            error_msg = f"❌ 输入格式有误：{e}"
            await interaction.response.send_message(
                error_msg, ephemeral=True, delete_after=60
            )
            return

        # 验证通过后，将原始字符串字典传递给回调函数
        await safe_defer(interaction)
        await self.submit_callback(interaction, raw_values)
