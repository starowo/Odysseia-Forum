"""Banner 事件监听器 —— 订阅 View 分发的自定义事件并协调 Service + Discord I/O。"""

import asyncio
import json
import logging
import os
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel import select as sm_select

from banner.banner_service import BannerService
from banner.channel_sync import ChannelSyncService
from banner.views.channel_selection_view import ChannelSelectionView
from banner.views.review_embed_builder import ReviewEmbedBuilder
from banner.views.review_view import ReviewView
from core.banner_application_repository import BannerApplicationRepository
from core.thread_repository import ThreadRepository
from models.banner_application import BannerApplication
from models.channel import Channel
from shared.enum import TargetType
from shared.redis_client import RedisManager

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class BannerEventListener(commands.Cog):
    """监听 banner 相关自定义事件，持有 Service 和 View 构建器。"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        # 与 Bot 启动使用相同凭据，为未入库频道提供按需索引。
        bot_token = os.environ.get("BOT_TOKEN", "").strip()
        self.channel_sync = ChannelSyncService(bot_token) if bot_token else None
        logger.info("Banner事件监听器已加载")

    async def cog_load(self):
        """Cog 加载时启动后台任务。"""
        self._consume_banner_review_queue.start()
        logger.info("Banner 审核队列消费者已启动")

    async def cog_unload(self):
        """Cog 卸载时停止后台任务。"""
        self._consume_banner_review_queue.cancel()

    # ── Banner 审核队列消费 ────────────────────────────────────

    @tasks.loop(seconds=1)
    async def _consume_banner_review_queue(self):
        """后台循环：消费 Redis 中的 banner 审核消息队列，发送审核消息到 Discord。"""
        redis = RedisManager.get_client()
        banner_conf = self.config

        try:
            result = await redis.brpop("banner:review:queue", timeout=5)  # type: ignore[return-type]
            if result is None:
                return
            _, payload = result
            data = json.loads(payload)
            application_id = data["application_id"]

            async with self.session_factory() as session:
                stmt = sm_select(BannerApplication).where(
                    BannerApplication.id == application_id
                )
                r = await session.execute(stmt)
                application = r.scalar_one_or_none()
                if application is None:
                    logger.warning(f"审核队列中的申请已不存在: {application_id}")
                    return

                # 构建审核 Embed 并发送到审核频道
                # 根据 target_type 获取 guild_id
                if application.target_type == TargetType.CHANNEL.value:
                    channel_result = await session.execute(
                        sm_select(Channel).where(
                            Channel.channel_id == application.thread_id
                        )
                    )
                    channel = channel_result.scalar_one_or_none()
                    guild_id = channel.guild_id if channel else None
                else:
                    repo = ThreadRepository(session)
                    guild_id = await repo.get_thread_guild_id(application.thread_id)
                resolved_cover_url = application.cover_image_url
                if (
                    resolved_cover_url is None
                    and application.target_type == TargetType.THREAD.value
                ):
                    thread = await ThreadRepository(session).get_thread_with_tags(
                        application.thread_id
                    )
                    if thread and thread.thumbnail_urls:
                        resolved_cover_url = thread.thumbnail_urls[0]
                # 查询历史申请记录
                app_repo = BannerApplicationRepository(session)
                history = await app_repo.get_history_by_thread_id(application.thread_id)

                embed = ReviewEmbedBuilder.build_review_embed(
                    application=application,
                    config=banner_conf,
                    guild_id=guild_id,
                    history=history if history else None,
                    resolved_cover_image_url=resolved_cover_url,
                )
                review_thread_id = banner_conf.get("review_thread_id")
                if review_thread_id:
                    review_channel = await self.bot.fetch_channel(review_thread_id)
                    if isinstance(review_channel, discord.Thread):
                        review_view = ReviewView()
                        review_message = await review_channel.send(
                            embed=embed, view=review_view
                        )
                        # 回填审核消息 ID
                        service = BannerService(session)
                        await service.update_review_message_info(
                            application.id,  # type: ignore[arg-type]
                            review_message.id,
                            review_thread_id,
                        )
                        await session.commit()
        except Exception:
            logger.error("消费 Banner 审核队列时出错", exc_info=True)
            await asyncio.sleep(5)

    @_consume_banner_review_queue.before_loop
    async def _before_consume_queue(self):
        """等待 bot 准备就绪后开始消费队列。"""
        await self.bot.wait_until_ready()

    # ── 表单提交 → 预验证 → 展示频道选择 ──────────────────────

    @commands.Cog.listener()
    async def on_banner_form_submit(
        self,
        interaction: discord.Interaction,
        target_id: int,
        cover_image_url: str | None,
        guild_id: int,
    ):
        """处理 banner_form_submit 事件：预验证目标 → 展示 ChannelSelectionView。"""
        try:
            async with self.session_factory() as session:
                service = BannerService(session, channel_sync=self.channel_sync)
                validation = await service.validate_application_request(
                    target_id=target_id,
                    guild_id=guild_id,
                    applicant_id=interaction.user.id,
                    cover_image_url=cover_image_url,
                )

                if not validation.success:
                    await interaction.followup.send(
                        f"❌ {validation.message}", ephemeral=True
                    )
                    return

                # 渠道目标使用 target_name，论坛帖子使用 thread.title
                if validation.target_type == TargetType.CHANNEL.value:
                    target_title = validation.target_name
                    target_channel_id = target_id
                elif validation.thread:
                    target_title = validation.thread.title
                    target_channel_id = validation.thread.channel_id
                else:
                    await interaction.followup.send(
                        "❌ 无法获取有效的目标信息，请检查链接或ID并联系管理员。",
                        ephemeral=True,
                    )
                    return

            # 构建目标链接
            target_link = f"https://discord.com/channels/{guild_id}/{target_id}"

            # 展示频道选择视图
            view = ChannelSelectionView(
                available_channels=self.config.get("available_channels", {}),
                thread_id=target_id,
                channel_id=target_channel_id,
                cover_image_url=cover_image_url,
                applicant_id=interaction.user.id,
                thread_title=target_title,
                thread_link=target_link,
                guild_id=guild_id,
            )
            await view.send_to(interaction)

        except Exception:
            logger.error("处理 banner_form_submit 事件时出错", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ 处理申请时出错，请稍后重试", ephemeral=True
                )
            except Exception:
                pass

    # ── 频道选择 → 创建申请 → 发送审核消息 ──────────────────────

    @commands.Cog.listener()
    async def on_banner_apply(
        self,
        interaction: discord.Interaction,
        thread_id: int,
        cover_image_url: str | None,
        target_scope: str,
        applicant_id: int,
        channel_id: int,
        guild_id: int = 0,
    ):
        """处理 banner_apply 事件：创建申请 → 发送审核消息 → 通知用户。"""
        try:
            async with self.session_factory() as session:
                service = BannerService(session, channel_sync=self.channel_sync)

                result = await service.validate_and_create_application(
                    target_id=thread_id,
                    guild_id=guild_id,
                    applicant_id=applicant_id,
                    cover_image_url=cover_image_url,
                    target_scope=target_scope,
                )

                if not result.success:
                    await interaction.followup.send(
                        f"❌ {result.message}", ephemeral=True
                    )
                    return

                application = result.application
                if application is None or application.id is None:
                    await interaction.followup.send(
                        "❌ 申请创建失败，请重试", ephemeral=True
                    )
                    return

                # 获取目标所属服务器 ID
                if application.target_type == TargetType.CHANNEL.value:
                    channel_result = await session.execute(
                        sm_select(Channel).where(
                            Channel.channel_id == application.thread_id
                        )
                    )
                    channel = channel_result.scalar_one_or_none()
                    thread_guild_id = channel.guild_id if channel else guild_id
                else:
                    repo = ThreadRepository(session)
                    thread_guild_id = await repo.get_thread_guild_id(thread_id)
                resolved_cover_url = application.cover_image_url
                if (
                    resolved_cover_url is None
                    and application.target_type == TargetType.THREAD.value
                ):
                    thread = await ThreadRepository(session).get_thread_with_tags(
                        application.thread_id
                    )
                    if thread and thread.thumbnail_urls:
                        resolved_cover_url = thread.thumbnail_urls[0]

                # 查询历史申请记录
                app_repo = BannerApplicationRepository(session)
                history = await app_repo.get_history_by_thread_id(application.thread_id)

                # 构建审核 Embed
                embed = ReviewEmbedBuilder.build_review_embed(
                    application=application,
                    config=self.config,
                    guild_id=thread_guild_id,
                    history=history if history else None,
                    resolved_cover_image_url=resolved_cover_url,
                )

                # 发送到审核频道
                review_thread_id = self.config.get("review_thread_id")
                if not review_thread_id:
                    await interaction.followup.send(
                        "❌ 审核频道未配置，请联系管理员", ephemeral=True
                    )
                    return

                review_channel = await self.bot.fetch_channel(review_thread_id)
                if not isinstance(review_channel, discord.Thread):
                    await interaction.followup.send(
                        "❌ 审核频道配置错误", ephemeral=True
                    )
                    return

                review_view = ReviewView()
                review_message = await review_channel.send(
                    embed=embed, view=review_view
                )

                # 回填审核消息 ID
                await service.update_review_message_info(
                    application.id, review_message.id, review_thread_id
                )
                await session.commit()

            await interaction.followup.send(
                "✅ 申请已提交！审核员将尽快处理您的申请。", ephemeral=True
            )

        except Exception:
            logger.error("处理 banner_apply 事件时出错", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ 提交申请时发生错误，请稍后重试", ephemeral=True
                )
            except Exception:
                pass

    # ── 审核：批准 ────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_banner_review_approve(
        self,
        interaction: discord.Interaction,
        reviewer_id: int,
    ):
        """处理 banner_review_approve 事件：通过消息 ID 查找申请 → 批准。"""
        await interaction.response.defer(ephemeral=True)

        try:
            async with self.session_factory() as session:
                service = BannerService(session)
                application = await service.get_application_by_review_message(
                    interaction.message.id
                )

                if not application:
                    await interaction.followup.send(
                        "❌ 找不到对应的申请记录，可能已被处理或数据丢失",
                        ephemeral=True,
                    )
                    return

                if application.status != "pending":
                    await interaction.followup.send(
                        f"❌ 该申请已被处理，当前状态: {application.status}",
                        ephemeral=True,
                    )
                    return

                application_id = application.id
                if application_id is None:
                    await interaction.followup.send("❌ 申请数据异常", ephemeral=True)
                    return

                application, entered_carousel = await service.approve_application(
                    application_id, reviewer_id
                )

                # 更新审核消息
                original_embed = interaction.message.embeds[0]
                original_embed.color = discord.Color.green()
                status_text = (
                    "✅ 已同意 - 已加入轮播"
                    if entered_carousel
                    else "✅ 已同意 - 已加入等待列表"
                )
                original_embed.add_field(
                    name="审核结果",
                    value=f"{status_text} by <@{reviewer_id}>",
                    inline=False,
                )
                await interaction.message.edit(embed=original_embed, view=None)

                # DM 通知
                try:
                    applicant = await self.bot.fetch_user(application.applicant_id)
                    dm_embed = ReviewEmbedBuilder.build_approve_dm(
                        application=application,
                        entered_carousel=entered_carousel,
                    )
                    await applicant.send(embed=dm_embed)
                except Exception:
                    logger.warning(
                        f"无法向申请者 {application.applicant_id} 发送 DM",
                        exc_info=True,
                    )

                # 存档
                await ReviewEmbedBuilder.archive_review(
                    bot=self.bot,
                    config=self.config,
                    application=application,
                    status=(
                        "approved_carousel" if entered_carousel else "approved_waitlist"
                    ),
                    reviewer_id=reviewer_id,
                )

            result_msg = "✅ 已同意申请并通知申请者"
            if entered_carousel:
                result_msg += "\n🎨 Banner已加入轮播列表"
            else:
                result_msg += "\n⏳ Banner已加入等待列表"
            await interaction.followup.send(result_msg, ephemeral=True)

        except Exception:
            logger.error("处理 banner_review_approve 事件时出错", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ 处理失败，请稍后重试", ephemeral=True
                )
            except Exception:
                pass

    # ── 审核：拒绝 ────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_banner_review_reject(
        self,
        interaction: discord.Interaction,
        reviewer_id: int,
        reason: str,
    ):
        """处理 banner_review_reject 事件：通过消息 ID 查找申请 → 拒绝。"""
        await interaction.response.defer(ephemeral=True)

        try:
            async with self.session_factory() as session:
                service = BannerService(session)
                application = await service.get_application_by_review_message(
                    interaction.message.id
                )

                if not application:
                    await interaction.followup.send(
                        "❌ 找不到对应的申请记录，可能已被处理或数据丢失",
                        ephemeral=True,
                    )
                    return

                if application.status != "pending":
                    await interaction.followup.send(
                        f"❌ 该申请已被处理，当前状态: {application.status}",
                        ephemeral=True,
                    )
                    return

                application_id = application.id
                if application_id is None:
                    await interaction.followup.send("❌ 申请数据异常", ephemeral=True)
                    return

                application = await service.reject_application(
                    application_id, reviewer_id, reason
                )

                # 更新审核消息
                original_embed = interaction.message.embeds[0]
                original_embed.color = discord.Color.red()
                original_embed.add_field(
                    name="审核结果",
                    value=f"❌ 已拒绝 by <@{reviewer_id}>",
                    inline=False,
                )
                original_embed.add_field(name="拒绝理由", value=reason, inline=False)
                await interaction.message.edit(embed=original_embed, view=None)

                # DM 通知
                try:
                    applicant = await self.bot.fetch_user(application.applicant_id)
                    dm_embed = ReviewEmbedBuilder.build_reject_dm(
                        application=application, reason=reason
                    )
                    await applicant.send(embed=dm_embed)
                except Exception:
                    logger.warning(
                        f"无法向申请者 {application.applicant_id} 发送 DM",
                        exc_info=True,
                    )

                # 存档
                await ReviewEmbedBuilder.archive_review(
                    bot=self.bot,
                    config=self.config,
                    application=application,
                    status="rejected",
                    reviewer_id=reviewer_id,
                )

            await interaction.followup.send("✅ 已拒绝申请并通知申请者", ephemeral=True)

        except Exception:
            logger.error("处理 banner_review_reject 事件时出错", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ 处理失败，请稍后重试", ephemeral=True
                )
            except Exception:
                pass
