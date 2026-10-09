from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from update_detector.cog import UpdateDetector


class PublishInfoModal(discord.ui.Modal):
    """收集新增或修改发布所需的描述与版本。"""

    def __init__(
        self,
        cog: "UpdateDetector",
        thread_id: int,
        message_link: str | None = None,
        update_id: int | None = None,
        description: str = "系统自动同步",
        version: str | None = None,
        prompt_message: discord.Message | None = None,
    ):
        super().__init__(title="修改发布信息", timeout=300)
        self.cog = cog
        self.thread_id = thread_id
        self.message_link = message_link
        self.update_id = update_id
        self.prompt_message = prompt_message
        self.description_input = discord.ui.TextInput(
            label="描述信息",
            default=description,
            min_length=1,
            max_length=500,
            style=discord.TextStyle.paragraph,
        )
        self.version_input = discord.ui.TextInput(
            label="版本号（可选）",
            default=version,
            required=False,
            max_length=50,
        )
        self.add_item(self.description_input)
        self.add_item(self.version_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """提交发布或编辑请求并刷新对应 Discord 消息。"""
        await interaction.response.defer(ephemeral=True)
        description = str(self.description_input.value)
        version = str(self.version_input.value).strip() or None
        if self.update_id is None:
            if self.message_link is None:
                await interaction.followup.send("缺少来源消息信息。", ephemeral=True)
                return
            await self.cog.publish_from_link(
                interaction,
                self.thread_id,
                self.message_link,
                description,
                version,
                send_overview=False,
            )
            if self.prompt_message:
                try:
                    await self.prompt_message.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass
            return
        await self.cog.edit_published_update(
            interaction,
            self.update_id,
            description,
            version,
        )
