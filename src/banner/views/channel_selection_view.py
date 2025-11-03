"""频道选择视图"""

import logging
import discord
from typing import TYPE_CHECKING
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.banner.banner_service import BannerService

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class ChannelSelectionView(discord.ui.View):
    """频道选择下拉视图"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        thread_id: int,
        channel_id: int,
        cover_image_url: str,
        applicant_id: int,
        config: dict,
    ):
        super().__init__(timeout=300)  # 5分钟超时
        self.bot = bot
        self.session_factory = session_factory
        self.thread_id = thread_id
        self.channel_id = channel_id
        self.cover_image_url = cover_image_url
        self.applicant_id = applicant_id
        self.config = config
        self.review_thread_id = config.get("review_thread_id")
        self.archive_thread_id = config.get("archive_thread_id")

        # 创建频道选择下拉菜单
        options = [
            discord.SelectOption(
                label="全频道",
                value="global",
                description="在所有频道展示（最多3个）",
                emoji="🌐",
            )
        ]

        # 转换available_channels从dict格式到list格式
        channels_dict = config.get("available_channels", {})
        for ch_id, ch_name in channels_dict.items():
            ch_config = {"id": ch_id, "name": ch_name}
            ch_id = ch_config.get("id")
            ch_name = ch_config.get("name", "未知频道")
            if ch_id:
                options.append(
                    discord.SelectOption(
                        label=ch_name,
                        value=str(ch_id),
                        description=f"仅在{ch_name}展示（最多5个）",
                        emoji="📋",
                    )
                )

        self.channel_select.options = options

    @discord.ui.select(placeholder="选择展示范围...")
    async def channel_select(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """处理频道选择"""
        await interaction.response.defer(ephemeral=True)

        try:
            target_scope = select.values[0]

            # 使用 service 验证并创建申请
            async with self.session_factory() as session:
                service = BannerService(session)
                result = await service.validate_and_create_application(
                    thread_id=self.thread_id,
                    applicant_id=self.applicant_id,
                    cover_image_url=self.cover_image_url,
                    target_scope=target_scope,
                )

                if not result.success:
                    await interaction.followup.send(
                        f"❌ {result.message}", ephemeral=True
                    )
                    return

                application = result.application

            # 使用共享函数发送审核消息
            from src.banner.banner_service import send_review_message

            success = await send_review_message(
                bot=self.bot,
                session_factory=self.session_factory,
                application=application,
                config=self.config,
                guild_id=interaction.guild_id,
            )

            if not success:
                await interaction.followup.send(
                    "❌ 审核消息发送失败，但申请已创建。请联系管理员。", ephemeral=True
                )
                return

            # 禁用当前视图
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

            # 通知用户
            await interaction.followup.send(
                "✅ 申请已提交！审核员将尽快处理您的申请。", ephemeral=True
            )

        except Exception as e:
            logger.error(f"处理频道选择时出错: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ 提交申请失败: {str(e)}", ephemeral=True
            )

    async def on_timeout(self):
        """超时处理"""
        for item in self.children:
            item.disabled = True
