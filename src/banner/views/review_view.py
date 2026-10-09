import logging

import discord

from shared.permissions import check_can_review_banner

logger = logging.getLogger(__name__)


class RejectReasonModal(discord.ui.Modal, title="拒绝理由"):
    """拒绝理由输入模态框"""

    reason = discord.ui.TextInput(
        label="请输入拒绝理由",
        style=discord.TextStyle.paragraph,
        placeholder="请详细说明拒绝原因...",
        required=True,
        max_length=500,
    )

    def __init__(self, original_interaction: discord.Interaction):
        super().__init__()
        self._original_interaction = original_interaction

    async def on_submit(self, interaction: discord.Interaction):
        """提交拒绝理由 → 分发 banner_review_reject 事件。"""
        interaction.client.dispatch(
            "banner_review_reject",
            interaction,
            interaction.user.id,  # reviewer_id
            str(self.reason.value),
        )


class ReviewView(discord.ui.View):
    """审核按钮持久化视图 —— 通过消息 ID 关联申请记录，分发事件处理。"""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="同意",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="banner_approve_button",
    )
    async def approve_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """同意按钮 → 分发 banner_review_approve 事件。"""
        # 权限检查：需要服务器管理员或Bot管理员
        if not await check_can_review_banner(interaction):
            await interaction.response.send_message(
                "❌ 您没有审核权限。需要服务器管理员或Bot管理员权限。",
                ephemeral=True,
            )
            return

        interaction.client.dispatch(
            "banner_review_approve",
            interaction,
            interaction.user.id,  # reviewer_id
        )

    @discord.ui.button(
        label="拒绝",
        style=discord.ButtonStyle.danger,
        emoji="❌",
        custom_id="banner_reject_button",
    )
    async def reject_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """拒绝按钮 → 弹出理由输入框，理由提交后分发事件。"""
        if not await check_can_review_banner(interaction):
            await interaction.response.send_message(
                "❌ 您没有审核权限。需要服务器管理员或Bot管理员权限。",
                ephemeral=True,
            )
            return

        modal = RejectReasonModal(original_interaction=interaction)
        await interaction.response.send_modal(modal)
