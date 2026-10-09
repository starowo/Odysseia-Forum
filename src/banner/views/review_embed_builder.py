import logging
from typing import TYPE_CHECKING, List, Optional

import discord

from shared.enum import ApplicationStatus, TargetType

if TYPE_CHECKING:
    from models import BannerApplication

logger = logging.getLogger(__name__)


class ReviewEmbedBuilder:
    """构建审核相关的 Discord Embed"""

    @staticmethod
    def build_review_embed(
        application: "BannerApplication",
        config: dict,
        guild_id: int | None,
        history: Optional[List["BannerApplication"]] = None,
        resolved_cover_image_url: str | None = None,
    ) -> discord.Embed:
        """构建审核频道中展示的 Banner 申请 Embed。"""
        # 展示范围文本
        target_scope = application.target_scope
        if target_scope == "global":
            scope_text = "全频道"
        else:
            channels_dict = config.get("available_channels", {})
            scope_text = channels_dict.get(target_scope, f"频道 {target_scope}")

        embed = discord.Embed(
            title="🎨 新的Banner申请",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="申请人", value=f"<@{application.applicant_id}>", inline=True
        )
        embed.add_field(name="展示范围", value=scope_text, inline=True)

        # 根据 target_type 构建目标链接
        is_channel = application.target_type == TargetType.CHANNEL.value
        target_label = "频道" if is_channel else "帖子"

        if guild_id:
            target_link = (
                f"https://discord.com/channels/{guild_id}/{application.thread_id}"
            )
            embed.add_field(name=target_label, value=target_link, inline=False)
        else:
            embed.add_field(
                name=f"{target_label}ID", value=str(application.thread_id), inline=False
            )

        cover_image_url = application.cover_image_url or resolved_cover_image_url
        if cover_image_url:
            embed.set_image(url=cover_image_url)

        # 历史记录
        if history:
            lines: list[str] = []
            for h in history:
                if h.review_thread_id and h.review_message_id and guild_id:
                    jump_url = (
                        f"https://discord.com/channels/{guild_id}"
                        f"/{h.review_thread_id}/{h.review_message_id}"
                    )
                    link = f"[#{h.id}]({jump_url})"
                else:
                    link = f"#{h.id}"

                if h.status == ApplicationStatus.APPROVED.value:
                    status_icon = "✅"
                elif h.status == ApplicationStatus.REJECTED.value:
                    status_icon = "❌"
                else:
                    status_icon = "❓"

                lines.append(f"{link} — {status_icon} {h.status}")

            embed.add_field(
                name="📋 历史记录",
                value="\n".join(lines),
                inline=False,
            )

        embed.set_footer(text=f"申请ID: {application.id}")
        return embed

    @staticmethod
    def build_approve_dm(
        application: "BannerApplication",
        entered_carousel: bool,
    ) -> discord.Embed:
        """构建批准后发给申请者的 DM Embed。"""
        embed = discord.Embed(
            title="Banner申请已通过",
            description=f"您的Banner申请（ID: {application.id}）已被批准！",
            color=discord.Color.green(),
        )
        if entered_carousel:
            embed.add_field(
                name="状态",
                value="您的Banner已加入轮播列表，将展示3天。",
                inline=False,
            )
        else:
            embed.add_field(
                name="状态",
                value="由于当前轮播列表已满，您的Banner已加入等待列表。待有空位时将自动展示。",
                inline=False,
            )
        return embed

    @staticmethod
    def build_reject_dm(
        application: "BannerApplication",
        reason: str,
    ) -> discord.Embed:
        """构建拒绝后发给申请者的 DM Embed。"""
        embed = discord.Embed(
            title="Banner申请被拒绝",
            description=f"您的Banner申请（ID: {application.id}）已被审核员拒绝。",
            color=discord.Color.red(),
        )
        embed.add_field(name="拒绝理由", value=reason, inline=False)
        return embed

    @staticmethod
    async def archive_review(
        bot,
        config: dict,
        application: "BannerApplication",
        status: str,
        reviewer_id: int,
    ) -> None:
        """在存档频道留档审核记录。"""
        archive_thread_id = config.get("archive_thread_id")
        if not archive_thread_id:
            logger.warning("存档频道未配置，跳过审核记录留档")
            return

        archive_channel = bot.get_channel(archive_thread_id)
        if archive_channel is None:
            try:
                archive_channel = await bot.fetch_channel(archive_thread_id)
            except Exception:
                logger.error("存档频道不存在，无法发送审核记录")
                return

        if not hasattr(archive_channel, "send"):
            logger.error("存档频道不支持发送消息")
            return

        guild = getattr(archive_channel, "guild", None)
        if guild is None:
            logger.error("无法获取存档频道所属服务器信息")
            return

        # 根据 target_type 构建链接
        if application.target_type == TargetType.CHANNEL.value:
            # 频道链接：guild/channel_id
            thread_url = (
                f"https://discord.com/channels/{guild.id}/{application.thread_id}"
            )
        else:
            # 论坛帖子链接：guild/channel_id/thread_id
            thread_url = (
                f"https://discord.com/channels/{guild.id}"
                f"/{application.channel_id}/{application.thread_id}"
            )

        status_display_map = {
            "approved_carousel": "✅ 已同意 - 已加入轮播",
            "approved_waitlist": "✅ 已同意 - 已加入等待列表",
            "rejected": "❌ 已拒绝",
        }
        color_map = {
            "approved_carousel": discord.Color.green(),
            "approved_waitlist": discord.Color.green(),
            "rejected": discord.Color.red(),
        }

        embed = discord.Embed(
            title=f"Banner审核 - {application.id}",
            description=status_display_map.get(status, status),
            color=color_map.get(status, discord.Color.blurple()),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="申请人",
            value=f"<@{application.applicant_id}>",
            inline=True,
        )
        embed.add_field(
            name="审核员",
            value=f"<@{reviewer_id}>",
            inline=True,
        )
        embed.add_field(name="申请ID", value=str(application.id), inline=True)
        embed.add_field(
            name="帖子链接",
            value=f"[点击查看]({thread_url})",
            inline=False,
        )
        if application.reject_reason:
            embed.add_field(
                name="拒绝理由",
                value=application.reject_reason,
                inline=False,
            )
        if application.cover_image_url:
            embed.set_image(url=application.cover_image_url)

        try:
            await archive_channel.send(embed=embed)
        except Exception:
            logger.error("存档审核记录时出错", exc_info=True)
