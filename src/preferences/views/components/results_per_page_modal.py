from typing import TYPE_CHECKING

import discord

from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from preferences.preferences_service import PreferencesService
    from preferences.views.preferences_view import PreferencesView


class ResultsPerPageModal(discord.ui.Modal, title="设置每页结果数量"):
    def __init__(
        self,
        service: "PreferencesService",
        parent_view: "PreferencesView",
        current_page_size: int,
    ):
        super().__init__()
        self.service = service
        self.parent_view = parent_view

        self.page_size_input = discord.ui.TextInput(
            label="每页结果数量 (3-9)",
            placeholder="输入一个3到9之间的数字",
            default=str(current_page_size),
            max_length=1,
            required=True,
        )
        self.add_item(self.page_size_input)

    async def on_submit(self, interaction: discord.Interaction):
        await safe_defer(interaction)
        try:
            num = int(self.page_size_input.value)
            if not (3 <= num <= 9):
                await self.service.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        "❌ 每页结果数量必须在3到9之间。", ephemeral=True
                    ),
                    priority=1,
                )
                return

            await self.service.save_user_preferences(
                interaction.user.id, {"results_per_page": num}
            )
            await self.parent_view.refresh(interaction)
        except ValueError:
            await self.service.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "❌ 请输入有效的数字。", ephemeral=True
                ),
                priority=1,
            )
        except Exception as e:
            error_message = f"❌ 保存失败: {e}"
            await self.service.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    error_message, ephemeral=True
                ),
                priority=1,
            )
