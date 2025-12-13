from typing import List, Optional

import discord

from models import BotConfig


class ConfigEmbedBuilder:
    """构建与配置相关的 Discord Embed"""

    @staticmethod
    def build_config_panel_embed(
        selected_config: Optional[BotConfig], all_configs: List[BotConfig]
    ) -> discord.Embed:
        """为通用配置面板构建 embed"""
        embed = discord.Embed(
            title="⚙️ 机器人通用配置面板",
            description="使用下方的下拉菜单选择要查看或修改的配置项。",
            color=0x3498DB,
        )

        if selected_config:
            embed.add_field(
                name=f"📄 当前选中: {selected_config.type_str}",
                value=f"{selected_config.tips}",
                inline=False,
            )

            current_value = ""
            if selected_config.value_float is not None:
                current_value += f"**浮点值**: `{selected_config.value_float}`\n"
            if selected_config.value_int is not None:
                current_value += f"**整数值**: `{selected_config.value_int}`\n"

            if not current_value:
                current_value = "未设置"

            embed.add_field(name="当前值", value=current_value, inline=True)
        else:
            embed.description = "请从下方选择一个配置项。"

        # 将所有配置项的值概览作为 footer 或另一个 field
        overview = []
        for config in all_configs:
            val = (
                config.value_float
                if config.value_float is not None
                else config.value_int
            )
            overview.append(f"• {config.type_str}: {val}")

        if overview:
            embed.add_field(
                name="所有配置项概览", value="\n".join(overview), inline=False
            )

        embed.set_footer(text="选择配置项后，点击 '编辑' 按钮进行修改。")
        return embed
