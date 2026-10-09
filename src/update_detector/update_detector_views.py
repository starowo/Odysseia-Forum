import logging
from typing import TYPE_CHECKING

import discord

from update_detector.publish_info_modal import PublishInfoModal

if TYPE_CHECKING:
    from update_detector.cog import UpdateDetector

logger = logging.getLogger(__name__)


class UpdateDetectorView(discord.ui.View):
    """提供可跨 Bot 重启恢复的更新检测交互。"""

    def __init__(
        self,
        cog: "UpdateDetector",
        thread_id: int | None = None,
        author_id: int | None = None,
        message_link: str | None = None,
    ):
        super().__init__(timeout=None)
        self.cog = cog
        self.thread_id = thread_id
        self.author_id = author_id
        self.message_link = message_link

    async def _resolve_context(
        self, interaction: discord.Interaction
    ) -> tuple[int, int, str] | None:
        """从实时消息恢复持久化按钮需要的业务上下文。"""
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "此操作只能在帖子中使用。", ephemeral=True
            )
            return None
        thread_id = self.thread_id or interaction.channel.id
        author_id = self.author_id or await self.cog.get_index_author_id(thread_id)
        reference = interaction.message.reference if interaction.message else None
        source_message_id = reference.message_id if reference else None
        message_link = self.message_link
        if message_link is None and source_message_id is not None:
            message_link = self.cog.build_message_link(
                interaction.guild_id or 0,
                thread_id,
                source_message_id,
            )
        if author_id is None or message_link is None:
            await interaction.response.send_message(
                "无法恢复此次检测信息，请使用 `/发布更新到索引页`。",
                ephemeral=True,
            )
            return None
        if interaction.user.id != author_id:
            await interaction.response.send_message(
                "此操作仅帖子作者可用。", ephemeral=True
            )
            return None
        return thread_id, author_id, message_link

    async def _handle_interaction_check(self, interaction: discord.Interaction) -> bool:
        """兼容旧调用并校验当前操作用户是否为作者。"""
        author_id = self.author_id
        if author_id is None and isinstance(interaction.channel, discord.Thread):
            author_id = await self.cog.get_index_author_id(interaction.channel.id)
        if interaction.user.id != author_id:
            await interaction.response.send_message(
                "此操作仅帖子作者可用。", ephemeral=True
            )
            return False
        return True

    async def _delete_prompt(self, interaction: discord.Interaction) -> None:
        """尽力删除已处理的检测提示。"""
        if interaction.message:
            try:
                await interaction.message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass

    @discord.ui.button(
        label="修改信息并发布",
        style=discord.ButtonStyle.success,
        custom_id="update_detector:edit_publish",
        row=0,
    )
    async def edit_publish_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """打开发布信息编辑表单。"""
        context = await self._resolve_context(interaction)
        if context is None:
            return
        thread_id, _, message_link = context
        await interaction.response.send_modal(
            PublishInfoModal(
                cog=self.cog,
                thread_id=thread_id,
                message_link=message_link,
                prompt_message=interaction.message,
            )
        )

    @discord.ui.button(
        label="直接发布",
        style=discord.ButtonStyle.primary,
        custom_id="update_detector:publish",
        row=0,
    )
    async def publish_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """使用系统默认描述直接发布。"""
        context = await self._resolve_context(interaction)
        if context is None:
            return
        thread_id, _, message_link = context
        await interaction.response.defer(ephemeral=True)
        await self.cog.publish_from_link(
            interaction,
            thread_id,
            message_link,
            "系统自动同步",
            None,
            send_overview=False,
        )
        await self._delete_prompt(interaction)

    @discord.ui.button(
        label="跳过",
        style=discord.ButtonStyle.primary,
        custom_id="update_detector:skip",
        row=0,
    )
    async def skip_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """忽略本次检测提示。"""
        if await self._resolve_context(interaction) is None:
            return
        await interaction.response.defer(ephemeral=True)
        await self._delete_prompt(interaction)

    @discord.ui.button(
        label="发布且以后自动同步",
        style=discord.ButtonStyle.primary,
        custom_id="update_detector:auto_publish",
        row=0,
    )
    async def auto_publish_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """开启自动同步并发布当前更新。"""
        context = await self._resolve_context(interaction)
        if context is None:
            return
        thread_id, author_id, message_link = context
        await interaction.response.defer(ephemeral=True)
        await self.cog.set_user_auto_sync(author_id, thread_id, True)
        await self.cog.publish_from_link(
            interaction,
            thread_id,
            message_link,
            "系统自动同步",
            None,
            send_overview=False,
        )
        await self._delete_prompt(interaction)

    @discord.ui.button(
        label="不再提醒",
        style=discord.ButtonStyle.danger,
        custom_id="update_detector:no_remind",
        row=1,
    )
    async def no_remind_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """关闭当前作品的检测提醒。"""
        context = await self._resolve_context(interaction)
        if context is None:
            return
        thread_id, author_id, _ = context
        await interaction.response.defer(ephemeral=True)
        await self.cog.set_user_no_remind(author_id, thread_id, True)
        await interaction.followup.send(
            "已关闭此帖的更新提醒，可用 `/更新提醒设置 修改` 恢复。",
            ephemeral=True,
        )
        await self._delete_prompt(interaction)


def build_update_embed(
    prompt_message: str,
    description: str = "系统自动同步",
    version: str | None = None,
) -> discord.Embed:
    """构建更新发布信息预览。"""
    manual_publish_hint = (
        "索引页不一定每次更新都能检测到，您也可以使用 "
        "`/发布更新到索引页` 指令进行手动同步"
    )
    embed = discord.Embed(
        title="发布信息预览",
        description=f"{prompt_message}\n\n{manual_publish_hint}",
        color=discord.Color.blue(),
    )
    embed.add_field(name="描述信息", value=description, inline=False)
    if version:
        embed.add_field(name="版本号", value=version, inline=False)
    return embed
