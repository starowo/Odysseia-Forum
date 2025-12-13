from typing import TYPE_CHECKING, Dict

import discord

from models import BotConfig
from shared.enum.search_config_type import SearchConfigType

if TYPE_CHECKING:
    from config.general_config_handler import GeneralConfigHandler


class EditConfigModal(discord.ui.Modal, title="编辑配置项"):
    def __init__(self, handler: "GeneralConfigHandler", config_item: BotConfig):
        super().__init__(timeout=300)
        self.handler = handler
        self.config_item = config_item
        self.inputs: Dict[str, discord.ui.TextInput] = {}

        # --- 动态创建输入框 ---
        # 检查 value_float 字段
        if self.config_item.value_float is not None:
            float_input = discord.ui.TextInput(
                label=f"{self.config_item.type_str} (浮点数)",
                placeholder="请输入新的浮点数值",
                default=str(self.config_item.value_float),
                required=True,
            )
            self.add_item(float_input)
            self.inputs["value_float"] = float_input

        # 检查 value_int 字段
        if self.config_item.value_int is not None:
            int_input = discord.ui.TextInput(
                label=f"{self.config_item.type_str} (整数)",
                placeholder="请输入新的整数值",
                default=str(self.config_item.value_int),
                required=True,
            )
            self.add_item(int_input)
            self.inputs["value_int"] = int_input

        # 未来可以扩展到 config_str 等字段

    async def on_submit(self, interaction: discord.Interaction):
        new_values = {}
        try:
            if "value_float" in self.inputs:
                new_values["value_float"] = float(self.inputs["value_float"].value)
            if "value_int" in self.inputs:
                new_values["value_int"] = int(self.inputs["value_int"].value)
        except ValueError:
            await interaction.response.send_message(
                "❌ 输入的值格式不正确，请确保浮点数和整数格式无误。", ephemeral=True
            )
            return

        await self.handler.process_modal_submit(
            interaction, SearchConfigType(self.config_item.type), new_values
        )
