"""Banner申请表单Modal"""

import logging
import discord
from typing import TYPE_CHECKING
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.banner.banner_service import BannerService
from .channel_selection_view import ChannelSelectionView

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class ApplicationFormModal(discord.ui.Modal, title="Banner申请"):
    """Banner申请表单"""

    thread_id = discord.ui.TextInput(
        label="帖子ID",
        placeholder="请输入帖子的Thread ID（纯数字）",
        style=discord.TextStyle.short,
        required=True,
        min_length=17,
        max_length=20,
    )

    cover_image_url = discord.ui.TextInput(
        label="封面图链接（推荐16:9）",
        placeholder="https://...",
        style=discord.TextStyle.short,
        required=True,
    )

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
    ):
        super().__init__()
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.review_thread_id = config.get("review_thread_id")
        self.archive_thread_id = config.get("archive_thread_id")

        # 转换available_channels从dict格式到list格式
        channels_dict = config.get("available_channels", {})
        self.available_channels = [
            {"id": ch_id, "name": ch_name} for ch_id, ch_name in channels_dict.items()
        ]

    async def on_submit(self, interaction: discord.Interaction):
        """处理表单提交"""
        await interaction.response.defer(ephemeral=True)

        try:
            # 验证并解析帖子ID
            thread_id_str = str(self.thread_id.value).strip()
            if not thread_id_str.isdigit():
                await interaction.followup.send("❌ 帖子ID必须是纯数字", ephemeral=True)
                return

            thread_id = int(thread_id_str)
            cover_url = str(self.cover_image_url.value).strip()

            # 检查用户身份
            if not isinstance(interaction.user, discord.Member):
                await interaction.followup.send("❌ 无法验证您的身份", ephemeral=True)
                return

            # 使用 service 进行预验证（不创建申请，只验证）
            async with self.session_factory() as session:
                service = BannerService(session)
                # 先验证帖子和作者
                validation = await service.validate_application_request(
                    thread_id=thread_id,
                    applicant_id=interaction.user.id,
                    cover_image_url=cover_url,
                )

                if not validation.success:
                    await interaction.followup.send(
                        f"❌ {validation.message}", ephemeral=True
                    )
                    return

                thread = validation.thread

            # 显示频道选择视图
            view = ChannelSelectionView(
                bot=self.bot,
                session_factory=self.session_factory,
                thread_id=thread_id,
                channel_id=thread.channel_id,
                cover_image_url=cover_url,
                applicant_id=interaction.user.id,
                config=self.config,
            )

            # 构建Discord链接
            guild_id = interaction.guild_id or ""
            thread_link = f"https://discord.com/channels/{guild_id}/{thread_id}"

            embed = discord.Embed(
                title="选择展示范围",
                description="请选择您希望Banner展示的范围：",
                color=discord.Color.blue(),
            )
            embed.add_field(
                name="帖子",
                value=f"[{thread.title[:50]}]({thread_link})",
                inline=False,
            )
            embed.add_field(name="封面图", value=cover_url, inline=False)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"处理Banner申请表单时出错: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ 处理申请时出错: {str(e)}", ephemeral=True
            )
