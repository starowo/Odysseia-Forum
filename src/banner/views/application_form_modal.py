import logging

import discord

from shared.thread_link_parser import ThreadLinkParser

logger = logging.getLogger(__name__)


class ApplicationFormModal(discord.ui.Modal, title="Banner申请"):
    """Banner申请表单"""

    target_link = discord.ui.TextInput(
        label="帖子/赛事频道链接",
        placeholder="粘贴 Discord 跳转链接，或输入纯数字 ID",
        style=discord.TextStyle.short,
        required=True,
        min_length=17,
        max_length=150,
    )

    cover_image_url = discord.ui.TextInput(
        label="封面图链接（推荐16:9）",
        placeholder="帖子可留空并使用当前首图；频道必须填写",
        style=discord.TextStyle.short,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        """表单提交 → 校验格式 → 分发 banner_form_submit 事件。"""
        await interaction.response.defer(ephemeral=True)

        target_input = str(self.target_link.value).strip()
        parsed_target = ThreadLinkParser.parse_thread_link(
            target_input, interaction.guild_id or 0
        )
        if parsed_target is None:
            await interaction.followup.send(
                "❌ 请输入有效的 Discord 帖子/赛事频道链接或纯数字 ID",
                ephemeral=True,
            )
            return

        guild_id, target_id = parsed_target
        cover_url = str(self.cover_image_url.value).strip()

        interaction.client.dispatch(
            "banner_form_submit",
            interaction,
            target_id,
            cover_url,
            guild_id,
        )
