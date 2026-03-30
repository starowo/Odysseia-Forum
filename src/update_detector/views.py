import asyncio
import logging
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from update_detector.cog import UpdateDetector

logger = logging.getLogger(__name__)


class UpdateDetectorView(discord.ui.View):
    """更新检测提醒的按钮视图，带自动删除功能"""

    def __init__(
        self,
        cog: "UpdateDetector",
        thread_id: int,
        author_id: int,
        message_link: str,
        auto_delete_seconds: int = 600,
    ):
        super().__init__(timeout=auto_delete_seconds)
        self.cog = cog
        self.thread_id = thread_id
        self.author_id = author_id
        self.message_link = message_link
        self.auto_delete_seconds = auto_delete_seconds
        self._message: discord.Message | None = None

    def set_message(self, message: discord.Message):
        self._message = message

    async def on_timeout(self):
        await self._delete_message()

    async def _delete_message(self):
        if self._message:
            try:
                await self._message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            self._message = None

    async def _handle_interaction_check(
        self, interaction: discord.Interaction
    ) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "此操作仅帖子作者可用。", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="同步", style=discord.ButtonStyle.success, custom_id="ud_sync"
    )
    async def sync_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await self._handle_interaction_check(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        success = await self.cog.do_sync_update(self.thread_id, self.message_link)
        if success:
            await interaction.followup.send("✅ 已同步更新到索引页。", ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ 同步失败，帖子可能未被索引。", ephemeral=True
            )
        self.stop()
        await self._delete_message()

    @discord.ui.button(
        label="跳过", style=discord.ButtonStyle.secondary, custom_id="ud_skip"
    )
    async def skip_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await self._handle_interaction_check(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        self.stop()
        await self._delete_message()

    @discord.ui.button(
        label="以后自动同步",
        style=discord.ButtonStyle.primary,
        custom_id="ud_auto_sync",
    )
    async def auto_sync_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await self._handle_interaction_check(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        await self.cog.set_user_auto_sync(self.author_id, self.thread_id, True)
        success = await self.cog.do_sync_update(self.thread_id, self.message_link)
        if success:
            await interaction.followup.send(
                "✅ 已同步更新，并已开启此帖的自动同步。", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ 同步失败，但已开启此帖的自动同步。", ephemeral=True
            )
        self.stop()
        await self._delete_message()

    @discord.ui.button(
        label="不再提醒",
        style=discord.ButtonStyle.danger,
        custom_id="ud_no_remind",
    )
    async def no_remind_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await self._handle_interaction_check(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        await self.cog.set_user_no_remind(self.author_id, self.thread_id, True)
        await interaction.followup.send(
            "已关闭此帖的更新提醒。如需恢复，请使用 `/更新提醒设置` 指令。",
            ephemeral=True,
        )
        self.stop()
        await self._delete_message()


def build_update_embed(
    prompt_message: str,
    thread_name: str,
    auto_delete_seconds: int,
) -> discord.Embed:
    """构建更新检测提醒 Embed"""
    embed = discord.Embed(
        title="📦 发布更新检测",
        description=prompt_message,
        color=discord.Color.blue(),
    )
    embed.add_field(name="帖子", value=thread_name, inline=False)
    minutes = auto_delete_seconds // 60
    embed.set_footer(text=f"本消息 {minutes} 分钟后自动删除")
    return embed
