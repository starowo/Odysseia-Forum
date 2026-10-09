import logging

import discord

from banner.views.application_form_modal import ApplicationFormModal

logger = logging.getLogger(__name__)


class BannerApplicationButtonView(discord.ui.View):
    """Banner申请按钮持久化视图。"""

    def __init__(self, allowed_role_ids: list[int]):
        super().__init__(timeout=None)
        self.allowed_role_ids = allowed_role_ids

    @discord.ui.button(
        label="申请Banner展示",
        style=discord.ButtonStyle.primary,
        emoji="🎨",
        custom_id="banner_application_button",
    )
    async def application_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """处理申请按钮点击"""
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ 此功能仅在服务器中可用", ephemeral=True
            )
            return

        has_role = any(
            role.id in self.allowed_role_ids for role in interaction.user.roles
        )
        if not has_role and self.allowed_role_ids:
            await interaction.response.send_message(
                "❌ 您没有权限申请Banner展示。需要特定身份组。", ephemeral=True
            )
            return

        modal = ApplicationFormModal()
        await interaction.response.send_modal(modal)
