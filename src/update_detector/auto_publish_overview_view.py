from typing import TYPE_CHECKING

import discord

from update_detector.publish_info_modal import PublishInfoModal

if TYPE_CHECKING:
    from update_detector.cog import UpdateDetector


class AutoPublishOverviewView(discord.ui.View):
    """提供可跨重启恢复的自动发布概览操作。"""

    def __init__(self, cog: "UpdateDetector"):
        super().__init__(timeout=None)
        self.cog = cog

    async def _resolve(self, interaction: discord.Interaction):
        """按概览消息 ID 恢复更新记录并校验发布者。"""
        if interaction.message is None:
            return None
        update = await self.cog.get_update_by_overview(interaction.message.id)
        if update is None:
            await interaction.response.send_message(
                "此次发布已不存在。", ephemeral=True
            )
            return None
        if interaction.user.id != update.publisher_id:
            await interaction.response.send_message(
                "此操作仅发布者可用。", ephemeral=True
            )
            return None
        return update

    @discord.ui.button(
        label="修改发布信息",
        style=discord.ButtonStyle.primary,
        custom_id="update_overview:edit",
    )
    async def edit_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """打开已发布信息编辑表单。"""
        update = await self._resolve(interaction)
        if update is None:
            return
        await interaction.response.send_modal(
            PublishInfoModal(
                cog=self.cog,
                thread_id=update.thread_id,
                update_id=update.id,
                description=update.description,
                version=update.version,
            )
        )

    @discord.ui.button(
        label="删除此次发布",
        style=discord.ButtonStyle.danger,
        custom_id="update_overview:delete",
    )
    async def delete_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """撤销此次发布并将概览标记为已撤销。"""
        update = await self._resolve(interaction)
        if update is None:
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.delete_published_update(interaction, update.id)

    @discord.ui.button(
        label="关闭自动同步",
        style=discord.ButtonStyle.secondary,
        custom_id="update_overview:disable_auto",
    )
    async def disable_auto_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """关闭当前作品的自动同步偏好。"""
        update = await self._resolve(interaction)
        if update is None:
            return
        await interaction.response.defer(ephemeral=True)
        await self.cog.set_user_auto_sync(update.publisher_id, update.thread_id, False)
        await interaction.followup.send("已关闭此帖的自动同步。", ephemeral=True)


def build_overview_embed(
    description: str,
    version: str | None,
    message_link: str | None,
) -> discord.Embed:
    """构建自动发布后的公开概览。"""
    embed = discord.Embed(
        title="更新发布概览",
        description="检测到到您可能发布了作品的新版本，已自动同步到索引页。",
        color=discord.Color.green(),
    )
    embed.add_field(name="描述信息", value=description, inline=False)
    if version:
        embed.add_field(name="版本号", value=version, inline=False)
    return embed
