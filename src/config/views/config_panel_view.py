from typing import TYPE_CHECKING, List, Optional

import discord

from models import BotConfig
from shared.enum import SearchConfigType

if TYPE_CHECKING:
    from config.general_config_handler import GeneralConfigHandler


class ConfigPanelView(discord.ui.View):
    def __init__(
        self,
        handler: "GeneralConfigHandler",
        all_configs: List[BotConfig],
        initial_selection_type: SearchConfigType,
    ):
        super().__init__(timeout=600)
        self.handler = handler
        self.all_configs = all_configs
        self.selected_type = initial_selection_type
        self.update_components()

    @property
    def selected_config(self) -> Optional[BotConfig]:
        """获取当前选中的配置对象"""
        for config in self.all_configs:
            if config.type == self.selected_type:
                return config
        return None

    def update_components(self):
        """根据当前状态（尤其是 selected_type）更新所有组件"""
        self.clear_items()
        self.add_item(self.create_config_select())
        self.add_item(self.create_edit_button())
        self.add_item(self.create_close_button())

    def create_config_select(self) -> discord.ui.Select:
        """创建配置项选择下拉菜单"""
        options = []
        for config in self.all_configs:
            # TOTAL_DISPLAY_COUNT 是系统统计值，不应由用户直接配置
            if config.type == SearchConfigType.TOTAL_DISPLAY_COUNT:
                continue
            options.append(
                discord.SelectOption(
                    label=config.type_str,
                    description=config.tips[:100],  # description 最多100字符
                    value=str(config.type),  # value 必须是字符串
                    default=(config.type == self.selected_type),
                )
            )

        select = discord.ui.Select(
            placeholder="选择一个配置项进行查看或修改...",
            options=options,
            custom_id="config_select",
        )
        select.callback = self.on_config_select
        return select

    def create_edit_button(self) -> discord.ui.Button:
        """创建编辑按钮"""
        button = discord.ui.Button(
            label="✏️ 编辑", style=discord.ButtonStyle.primary, custom_id="edit_config"
        )
        # 如果选中的是不可编辑的项，则禁用按钮
        if (
            not self.selected_config
            or self.selected_type == SearchConfigType.TOTAL_DISPLAY_COUNT
        ):
            button.disabled = True
        button.callback = self.on_edit_click
        return button

    def create_close_button(self) -> discord.ui.Button:
        """创建关闭按钮"""
        button = discord.ui.Button(
            label="🔒 关闭",
            style=discord.ButtonStyle.secondary,
            custom_id="close_config",
        )
        button.callback = self.on_close_click
        return button

    async def on_config_select(self, interaction: discord.Interaction):
        """下拉菜单选择回调"""
        # 从 interaction 中获取选择的值
        selected_value = interaction.data["values"][0]  # type: ignore
        self.selected_type = SearchConfigType(int(selected_value))
        await self.handler.handle_selection_change(interaction, self)

    async def on_edit_click(self, interaction: discord.Interaction):
        """编辑按钮点击回调"""
        if self.selected_config:
            await self.handler.handle_edit_button(interaction, self.selected_config)

    async def on_close_click(self, interaction: discord.Interaction):
        """关闭按钮点击回调"""
        await interaction.response.defer()
        await interaction.delete_original_response()
