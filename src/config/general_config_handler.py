import logging
from typing import TYPE_CHECKING, Dict

import discord
from sqlalchemy.ext.asyncio import async_sessionmaker

from config.config_service import ConfigService
from config.embed_builder import ConfigEmbedBuilder
from config.views.components.edit_config_modal import EditConfigModal
from config.views.config_panel_view import ConfigPanelView
from models import BotConfig
from shared.enum.search_config_type import SearchConfigType
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class GeneralConfigHandler:
    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config_service: ConfigService,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config_service = config_service

    async def start_flow(self, interaction: discord.Interaction):
        """启动通用配置流程"""
        await safe_defer(interaction, ephemeral=True)

        all_configs = await self.config_service.get_all_configurable_search_configs()

        # 默认选中第一个可配置项
        initial_selection = SearchConfigType.UCB1_EXPLORATION_FACTOR

        view = ConfigPanelView(self, all_configs, initial_selection)
        embed = ConfigEmbedBuilder.build_config_panel_embed(
            view.selected_config, all_configs
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def handle_selection_change(
        self, interaction: discord.Interaction, view: ConfigPanelView
    ):
        """处理下拉菜单的选择变化"""
        await safe_defer(interaction, ephemeral=True)

        view.update_components()  # 更新视图（主要是下拉框的默认值和按钮状态）
        embed = ConfigEmbedBuilder.build_config_panel_embed(
            view.selected_config, view.all_configs
        )

        await interaction.edit_original_response(embed=embed, view=view)

    async def handle_edit_button(
        self, interaction: discord.Interaction, selected_config: BotConfig
    ):
        """处理编辑按钮点击，弹出模态框"""
        modal = EditConfigModal(self, selected_config)
        await interaction.response.send_modal(modal)

    async def process_modal_submit(
        self,
        interaction: discord.Interaction,
        config_type: SearchConfigType,
        new_values: Dict,
    ):
        """处理模态框提交，更新数据库，发布事件，并刷新视图"""
        await safe_defer(interaction, ephemeral=True)
        try:
            # 更新数据库
            updated = await self.config_service.update_search_config(
                config_type, new_values, interaction.user.id
            )
            if not updated:
                await interaction.followup.send(
                    "❌ 更新配置失败，未找到对应配置项。", ephemeral=True
                )
                return

            # 发布事件，通知所有监听者
            self.bot.dispatch("config_updated")

            await interaction.followup.send(
                "✅ 配置已成功更新！正在刷新面板...", ephemeral=True
            )

            # 刷新UI
            all_configs = (
                await self.config_service.get_all_configurable_search_configs()
            )

            original_message = await interaction.original_response()
            view = ConfigPanelView(self, all_configs, config_type)
            embed = ConfigEmbedBuilder.build_config_panel_embed(
                view.selected_config, all_configs
            )
            await original_message.edit(content=None, embed=embed, view=view)

        except Exception as e:
            logger.error(f"更新配置时出错: {e}", exc_info=True)
            await interaction.followup.send(f"❌ 更新失败: {e}", ephemeral=True)
