"""频道选择视图"""

import logging

import discord

logger = logging.getLogger(__name__)


class ChannelSelectionView(discord.ui.View):
    """频道选择下拉视图"""

    def __init__(
        self,
        available_channels: dict,
        thread_id: int,
        channel_id: int,
        cover_image_url: str | None,
        applicant_id: int,
        thread_title: str,
        thread_link: str,
        guild_id: int = 0,
    ):
        super().__init__(timeout=300)
        self._thread_id = thread_id
        self._channel_id = channel_id
        self._cover_image_url = cover_image_url
        self._applicant_id = applicant_id
        self._guild_id = guild_id

        # 构建下拉选项
        options = [
            discord.SelectOption(
                label="全频道",
                value="global",
                description="在所有频道展示（最多3个）",
                emoji="🌐",
            )
        ]
        for ch_id, ch_name in available_channels.items():
            options.append(
                discord.SelectOption(
                    label=ch_name,
                    value=str(ch_id),
                    description=f"仅在{ch_name}展示（最多5个）",
                    emoji="📋",
                )
            )
        self.channel_select.options = options

        # 构建预览 Embed
        embed = discord.Embed(
            title="选择展示范围",
            description="请选择您希望Banner展示的范围：",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="帖子",
            value=f"[{thread_title[:50]}]({thread_link})",
            inline=False,
        )
        embed.add_field(
            name="封面图",
            value=cover_image_url or "将动态使用帖子当前首图",
            inline=False,
        )
        self._preview_embed = embed

    async def send_to(self, interaction: discord.Interaction):
        """发送选择视图给用户。"""
        await interaction.followup.send(
            embed=self._preview_embed, view=self, ephemeral=True
        )

    @discord.ui.select(placeholder="选择展示范围...")
    async def channel_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """用户选择频道 → 分发 banner_apply 事件。"""
        await interaction.response.defer(ephemeral=True)

        target_scope = select.values[0]

        # 禁用当前视图
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(view=self)

        interaction.client.dispatch(
            "banner_apply",
            interaction,
            self._thread_id,
            self._cover_image_url,
            target_scope,
            self._applicant_id,
            self._channel_id,
            self._guild_id,
        )

    async def on_timeout(self):
        """超时禁用。"""
        for item in self.children:
            item.disabled = True
