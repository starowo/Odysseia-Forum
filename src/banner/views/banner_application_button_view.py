"""Banner申请按钮视图"""

import logging
import discord
from typing import TYPE_CHECKING
from sqlalchemy.ext.asyncio import async_sessionmaker

from .application_form_modal import ApplicationFormModal

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class BannerApplicationButtonView(discord.ui.View):
    """Banner申请按钮持久化视图"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.session_factory = session_factory
        self.config = config

        # 解析申请人身份组ID列表（逗号分隔的字符串）
        applicant_role_ids_str = config.get("applicant_role_ids", "")
        self.allowed_role_ids = [
            int(rid.strip()) for rid in applicant_role_ids_str.split(",") if rid.strip()
        ]

        self.review_thread_id = config.get("review_thread_id")
        self.archive_thread_id = config.get("archive_thread_id")

        # 转换available_channels从dict格式到list格式
        channels_dict = config.get("available_channels", {})
        self.available_channels = [
            {"id": ch_id, "name": ch_name} for ch_id, ch_name in channels_dict.items()
        ]

    @discord.ui.button(
        label="申请Banner展示",
        style=discord.ButtonStyle.primary,
        emoji="🎨",
        custom_id="banner_application_button",
    )
    async def application_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """处理申请按钮点击"""
        # 检查用户是否有指定身份组
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ 此功能仅在服务器中可用", ephemeral=True
            )
            return

        has_role = any(
            role.id in self.allowed_role_ids for role in interaction.user.roles
        )
        if not has_role and self.allowed_role_ids:
            await interaction.response.send_message(
                "❌ 您没有权限申请Banner展示。需要特定身份组。", ephemeral=True
            )
            return

        # 显示申请表单
        modal = ApplicationFormModal(
            bot=self.bot,
            session_factory=self.session_factory,
            config=self.config,
        )
        await interaction.response.send_modal(modal)
