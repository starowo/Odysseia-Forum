import discord
from typing import TYPE_CHECKING

from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from ..preferences_view import PreferencesView
    from ...preferences_service import PreferencesService


class TimeRangeModal(discord.ui.Modal, title="设置时间范围"):
    """用于输入时间范围的模态框"""

    after_date_input = discord.ui.TextInput(
        label="开始日期 (YYYY-MM-DD)",
        placeholder="例如: 2020-01-01。留空则不限制。",
        required=False,
        max_length=10,
    )
    before_date_input = discord.ui.TextInput(
        label="结束日期 (YYYY-MM-DD)",
        placeholder="例如: 2050-12-31。留空则不限制。",
        required=False,
        max_length=10,
    )

    def __init__(
        self,
        handler: "PreferencesService",
        view: "PreferencesView",
        current_after: str = "",
        current_before: str = "",
    ):
        super().__init__(timeout=900)
        self.handler = handler
        self.view = view
        self.after_date_input.default = current_after
        self.before_date_input.default = current_before

    async def on_submit(self, interaction: discord.Interaction):
        await safe_defer(interaction)

        after_str = self.after_date_input.value
        before_str = self.before_date_input.value

        try:
            await self.handler.update_user_time_range(
                user_id=interaction.user.id,
                after_date_str=after_str,
                before_date_str=before_str,
            )
        except ValueError:
            await interaction.followup.send(
                "❌ 日期格式错误，请使用 YYYY-MM-DD 格式。", ephemeral=True
            )
            return

        # 业务逻辑成功后，刷新父视图
        await self.view.refresh(interaction)
