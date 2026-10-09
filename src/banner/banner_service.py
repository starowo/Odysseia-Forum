"""Banner申请和管理服务"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from banner.channel_sync import ChannelSyncService
from banner.dto.application_result import ApplicationResult
from banner.dto.banner_scope_status import BannerScopeStatus
from banner.dto.banner_status_item import BannerStatusItem
from banner.dto.delete_banner_result import DeleteBannerResult
from core.banner_application_repository import BannerApplicationRepository
from core.banner_carousel_repository import BannerCarouselRepository
from core.banner_waitlist_repository import BannerWaitlistRepository
from core.thread_repository import ThreadRepository
from dto.thread_dto import ThreadDTO
from models import (
    BannerApplication,
    BannerCarousel,
    Channel,
)
from shared.enum import ApplicationStatus, TargetType

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class BannerService:
    """Banner申请和轮播管理服务"""

    # 全频道最多3个banner
    GLOBAL_MAX_BANNERS = 3
    # 每个频道最多3个banner
    CHANNEL_MAX_BANNERS = 3
    # Banner展示时长：3天
    BANNER_DURATION_DAYS = 3

    def __init__(
        self,
        session: AsyncSession,
        channel_sync: Optional[ChannelSyncService] = None,
    ):
        self.session = session
        self.channel_sync = channel_sync
        self.app_repo = BannerApplicationRepository(session)
        self.carousel_repo = BannerCarouselRepository(session)
        self.waitlist_repo = BannerWaitlistRepository(session)

    async def get_status(
        self, configured_channel_ids: list[int], now: datetime
    ) -> list[BannerScopeStatus]:
        """批量生成全频道及各频道的管理状态快照。"""
        # 两次查询获取完整轮播和等待数量，并在会话内转换 DTO。
        banners = await self.carousel_repo.get_all_active_for_status(now)
        waiting_counts = await self.waitlist_repo.get_counts_by_scope()
        grouped: dict[int | None, list[BannerStatusItem]] = {}
        for banner in banners:
            grouped.setdefault(banner.channel_id, []).append(
                BannerStatusItem(
                    target_id=banner.thread_id,
                    target_type=banner.target_type,
                    title=banner.title,
                    end_time=banner.end_time,
                )
            )

        # 配置频道保留顺序，补充仍有记录的未配置频道。
        configured_ids = list(dict.fromkeys(configured_channel_ids))
        configured_id_set = set(configured_ids)
        recorded_ids = set(grouped) | set(waiting_counts)
        extra_ids = sorted(
            cid for cid in recorded_ids
            if cid is not None and cid not in configured_id_set
        )
        return [
            BannerScopeStatus(
                channel_id=cid,
                capacity=self.GLOBAL_MAX_BANNERS if cid is None else self.CHANNEL_MAX_BANNERS,
                waiting_count=waiting_counts.get(cid, 0),
                items=grouped.get(cid, []),
            )
            for cid in [None, *configured_ids, *extra_ids]
        ]

    async def validate_application_request(
        self,
        target_id: int,
        guild_id: int,
        applicant_id: int,
        cover_image_url: str | None,
        target_scope: Optional[str] = None,
    ) -> ApplicationResult:
        """验证Banner申请请求，自动检测目标类型（Thread / Channel / 按需索引）。"""
        cover_url = cover_image_url.strip() if cover_image_url else None
        if cover_url and not cover_url.startswith(("http://", "https://")):
            return ApplicationResult(
                success=False,
                message="封面图链接必须是有效的URL（以http://或https://开头）",
            )

        # 验证展示范围（如果提供）
        if target_scope is not None:
            scope = target_scope.strip()
            if scope != "global" and not scope.isdigit():
                return ApplicationResult(
                    success=False,
                    message="展示范围必须是'global'或有效的频道ID",
                )

        # 查 Thread 表 → 找到 → target_type=THREAD，检查作者
        thread_repo = ThreadRepository(self.session)
        thread = await thread_repo.get_thread_with_tags(target_id)
        if thread:
            if not thread.show_flag or thread.not_found_count > 0:
                return ApplicationResult(
                    success=False,
                    message="该帖子当前不可见，无法申请Banner",
                )
            if thread.author_id != applicant_id:
                return ApplicationResult(
                    success=False,
                    message="只能为自己的帖子申请Banner",
                )
            if cover_url is None and not thread.thumbnail_urls:
                return ApplicationResult(
                    success=False,
                    message="帖子没有可用首图，请提交自定义封面图",
                )
            return ApplicationResult(
                success=True,
                message="验证通过",
                thread=ThreadDTO.from_orm(thread),
                target_type=TargetType.THREAD.value,
                guild_id=thread.guild_id,
                target_name=thread.title,
            )

        # 查 Channel 表 → 找到 → target_type=CHANNEL，跳过作者检查
        channel_result = await self.session.execute(
            select(Channel).where(Channel.channel_id == target_id)
        )
        channel = channel_result.scalar_one_or_none()
        if channel:
            if cover_url is None:
                return ApplicationResult(
                    success=False,
                    message="频道Banner必须提交自定义封面图",
                )
            return ApplicationResult(
                success=True,
                message="验证通过",
                target_type=TargetType.CHANNEL.value,
                guild_id=channel.guild_id,
                target_name=channel.name,
            )

        # 都没找到 → ChannelSyncService 按需索引
        if self.channel_sync:
            channel = await self.channel_sync.fetch_and_index(self.session, target_id)
            if channel:
                if cover_url is None:
                    return ApplicationResult(
                        success=False,
                        message="频道Banner必须提交自定义封面图",
                    )
                return ApplicationResult(
                    success=True,
                    message="验证通过",
                    target_type=TargetType.CHANNEL.value,
                    guild_id=channel.guild_id,
                    target_name=channel.name,
                )

        return ApplicationResult(
            success=False,
            message="该帖子/频道未被索引，无法申请Banner。请确保ID正确。",
        )

    async def validate_and_create_application(
        self,
        target_id: int,
        guild_id: int,
        applicant_id: int,
        cover_image_url: str | None,
        target_scope: str,
    ) -> ApplicationResult:
        """验证并创建Banner申请。"""
        validation = await self.validate_application_request(
            target_id=target_id,
            guild_id=guild_id,
            applicant_id=applicant_id,
            cover_image_url=cover_image_url,
            target_scope=target_scope,
        )

        if not validation.success:
            return validation

        # 确定 channel_id：Thread 用帖子所属频道，Channel 用频道自身
        if validation.target_type == TargetType.CHANNEL.value:
            channel_id = target_id
        elif validation.thread:
            channel_id = validation.thread.channel_id
        else:
            channel_id = guild_id

        cover_url = cover_image_url.strip() if cover_image_url else None
        scope = target_scope.strip()

        application = await self.app_repo.create(
            thread_id=target_id,
            channel_id=channel_id,
            applicant_id=applicant_id,
            cover_image_url=cover_url,
            target_scope=scope,
            target_type=validation.target_type,
        )
        await self.session.commit()
        await self.session.refresh(application)

        logger.info(
            f"用户 {applicant_id} 提交了Banner申请，目标ID: {target_id}，"
            f"类型: {validation.target_type}，范围: {scope}"
        )

        validation.application = application
        return validation

    async def approve_application(
        self, application_id: int, reviewer_id: int
    ) -> Tuple[BannerApplication, bool]:
        """批准申请并将banner加入轮播或等待列表。"""
        application = await self.app_repo.get_by_id(application_id)
        if not application:
            raise ValueError("申请不存在")

        # 根据 target_type 获取标题
        if application.target_type == TargetType.CHANNEL.value:
            channel_result = await self.session.execute(
                select(Channel).where(Channel.channel_id == application.thread_id)
            )
            channel = channel_result.scalar_one_or_none()
            target_title = channel.name if channel else "未知频道"
        else:
            thread_repo = ThreadRepository(self.session)
            thread_obj = await thread_repo.get_thread_with_tags(application.thread_id)
            if not thread_obj:
                raise ValueError("帖子不存在")
            target_title = thread_obj.title

        # 更新申请状态
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        application.status = ApplicationStatus.APPROVED.value
        application.reviewed_at = now
        application.reviewer_id = reviewer_id

        # 判断是全频道还是特定频道
        is_global = application.target_scope == "global"
        channel_id = None if is_global else int(application.target_scope)

        # 检查当前轮播列表是否已满
        max_banners = self.GLOBAL_MAX_BANNERS if is_global else self.CHANNEL_MAX_BANNERS
        current_count = await self.carousel_repo.get_count(channel_id)

        if current_count < max_banners:
            await self.carousel_repo.add(
                thread_id=application.thread_id,
                channel_id=channel_id,
                cover_image_url=application.cover_image_url,
                title=target_title,
                duration_days=self.BANNER_DURATION_DAYS,
                target_type=application.target_type,
            )
            entered_carousel = True
        else:
            await self.waitlist_repo.add(
                thread_id=application.thread_id,
                channel_id=channel_id,
                cover_image_url=application.cover_image_url,
                title=target_title,
                target_type=application.target_type,
            )
            entered_carousel = False

        await self.session.commit()
        await self.session.refresh(application)
        return application, entered_carousel

    async def reject_application(
        self, application_id: int, reviewer_id: int, reason: str
    ) -> BannerApplication:
        """拒绝申请。"""
        application = await self.app_repo.get_by_id(application_id)
        if not application:
            raise ValueError("申请不存在")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        application.status = ApplicationStatus.REJECTED.value
        application.reviewed_at = now
        application.reviewer_id = reviewer_id
        application.reject_reason = reason

        await self.session.commit()
        await self.session.refresh(application)
        return application

    def _get_scope_capacity(self, channel_id: Optional[int]) -> int:
        """获取全频道或单频道范围的轮播容量。"""
        return (
            self.GLOBAL_MAX_BANNERS
            if channel_id is None
            else self.CHANNEL_MAX_BANNERS
        )

    async def _refill_scope_to_capacity(self, channel_id: Optional[int]) -> int:
        """在轮播存在空位时按 FIFO 从等待队列补足。"""
        current_count = await self.carousel_repo.get_count(channel_id)
        available_slots = max(0, self._get_scope_capacity(channel_id) - current_count)
        promoted_count = 0

        # 补位次数受范围容量约束，达到或超过容量时不再补位。
        for _ in range(available_slots):
            waitlist_item = await self.waitlist_repo.pop(channel_id)
            if waitlist_item is None:
                break
            await self.carousel_repo.add(
                thread_id=waitlist_item.thread_id,
                channel_id=waitlist_item.channel_id,
                cover_image_url=waitlist_item.cover_image_url,
                title=waitlist_item.title,
                duration_days=self.BANNER_DURATION_DAYS,
                target_type=waitlist_item.target_type,
            )
            promoted_count += 1

        return promoted_count

    async def cleanup_expired_banners(self) -> int:
        """清理过期的banner并从等待列表补充。"""
        expired = await self.carousel_repo.get_expired()

        affected_channel_ids: set[int | None] = set()
        for banner in expired:
            await self.carousel_repo.delete(banner)
            affected_channel_ids.add(banner.channel_id)

        # 每个受影响范围只计算一次空位，再按新容量补足。
        for channel_id in affected_channel_ids:
            await self._refill_scope_to_capacity(channel_id)

        await self.session.commit()
        return len(expired)

    async def delete_banner_by_thread(self, thread_id: int) -> DeleteBannerResult:
        """根据 thread_id 从轮播或等待列表中删除 Banner。"""
        carousel_items = await self.carousel_repo.get_by_thread(thread_id)
        waitlist_items = await self.waitlist_repo.get_by_thread(thread_id)

        if not carousel_items and not waitlist_items:
            return DeleteBannerResult(
                success=False,
                message="未找到该帖子ID对应的Banner记录，请在轮播列表或等待列表中确认。",
            )

        if len(carousel_items) + len(waitlist_items) > 1:
            parts = []
            for item in carousel_items:
                scope = (
                    "全频道" if item.channel_id is None else f"频道 {item.channel_id}"
                )
                parts.append(f"  • 轮播列表: {item.title[:40]} (范围: {scope})")
            for item in waitlist_items:
                scope = (
                    "全频道" if item.channel_id is None else f"频道 {item.channel_id}"
                )
                parts.append(f"  • 等待列表: {item.title[:40]} (范围: {scope})")
            return DeleteBannerResult(
                success=False,
                message="该帖子ID对应多条Banner记录，删除时存在歧义：\n"
                + "\n".join(parts),
            )

        if carousel_items:
            banner = carousel_items[0]
            channel_id = banner.channel_id
            title = banner.title
            scope_label = "全频道" if channel_id is None else f"频道 {channel_id}"

            await self.carousel_repo.delete(banner)
            promoted_count = await self._refill_scope_to_capacity(channel_id)

            await self.session.commit()

            return DeleteBannerResult(
                success=True,
                message=f"已从轮播列表中删除Banner「{title}」",
                deleted_from="carousel",
                thread_id=thread_id,
                banner_title=title,
                scope_label=scope_label,
                promoted_from_waitlist=promoted_count > 0,
            )

        if waitlist_items:
            banner = waitlist_items[0]
            channel_id = banner.channel_id
            title = banner.title
            scope_label = "全频道" if channel_id is None else f"频道 {channel_id}"

            await self.waitlist_repo.delete(banner)
            await self.session.commit()

            return DeleteBannerResult(
                success=True,
                message=f"已从等待列表中删除Banner「{title}」",
                deleted_from="waitlist",
                thread_id=thread_id,
                banner_title=title,
                scope_label=scope_label,
                promoted_from_waitlist=False,
            )

        return DeleteBannerResult(
            success=False,
            message="删除Banner时发生未预期的错误",
        )

    async def get_active_banners(
        self,
        channel_id: Optional[int] = None,
        channel_ids: Optional[List[int]] = None,
        all_channels: bool = False,
    ) -> List[BannerCarousel]:
        """兼容单频道调用并获取有序的多频道活跃 Banner。"""
        effective_channel_ids = list(channel_ids or [])
        if channel_id is not None:
            effective_channel_ids.append(channel_id)
        effective_channel_ids = list(dict.fromkeys(effective_channel_ids))
        return await self.carousel_repo.get_active(
            channel_ids=effective_channel_ids, all_channels=all_channels
        )

    async def update_review_message_info(
        self, application_id: int, review_message_id: int, review_thread_id: int
    ):
        """更新审核记录消息信息。"""
        updated = await self.app_repo.update_review_message_info(
            application_id, review_message_id, review_thread_id
        )
        if updated:
            await self.session.commit()

    async def get_application_by_review_message(
        self, review_message_id: int
    ) -> Optional[BannerApplication]:
        """通过审核消息ID获取申请记录。"""
        return await self.app_repo.get_by_review_message(review_message_id)


async def send_review_message(
    bot: "MyBot",
    session_factory,
    application: BannerApplication,
    config: dict,
    guild_id: Optional[int] = None,
) -> bool:
    """发送审核消息到指定的审核子区。"""
    import discord

    from banner.views.review_view import ReviewView

    review_thread_id = config.get("review_thread_id")
    if not review_thread_id:
        logger.error("审核Thread ID未配置")
        return False

    review_thread = bot.get_channel(review_thread_id)
    if review_thread is None:
        review_thread = await bot.fetch_channel(review_thread_id)
    if not isinstance(review_thread, discord.Thread):
        logger.error(f"审核Thread配置错误: {review_thread_id}")
        return False

    if not guild_id:
        guild_id = review_thread.guild.id

    # 获取展示范围名称
    target_scope = application.target_scope
    if target_scope == "global":
        scope_text = "全频道"
    else:
        channels_dict = config.get("available_channels", {})
        scope_text = channels_dict.get(target_scope, f"频道 {target_scope}")

    # 根据 target_type 构建目标链接
    if application.target_type == TargetType.CHANNEL.value:
        # 频道链接：https://discord.com/channels/{guild_id}/{channel_id}
        target_link = f"https://discord.com/channels/{guild_id}/{application.thread_id}"
        target_label = "频道"
    else:
        # 帖子链接：https://discord.com/channels/{guild_id}/{thread_id}
        target_link = f"https://discord.com/channels/{guild_id}/{application.thread_id}"
        target_label = "帖子"

    # 构建审核embed
    embed = discord.Embed(
        title="🎨 新的Banner申请",
        color=discord.Color.orange(),
    )
    embed.add_field(name="申请人", value=f"<@{application.applicant_id}>", inline=True)
    embed.add_field(name="展示范围", value=scope_text, inline=True)
    embed.add_field(name="类型", value=target_label, inline=True)
    embed.add_field(name=target_label, value=target_link, inline=False)
    review_cover_url = application.cover_image_url
    if review_cover_url is None and application.target_type == TargetType.THREAD.value:
        async with session_factory() as image_session:
            thread = await ThreadRepository(image_session).get_thread_with_tags(
                application.thread_id
            )
            if thread and thread.thumbnail_urls:
                review_cover_url = thread.thumbnail_urls[0]
    if review_cover_url:
        embed.set_image(url=review_cover_url)
    embed.set_footer(text=f"申请ID: {application.id}")

    # 创建审核视图
    review_view = ReviewView(
        bot=bot,
        session_factory=session_factory,
        config=config,
    )

    try:
        review_message = await review_thread.send(embed=embed, view=review_view)

        # 更新申请记录的消息ID
        async with session_factory() as session:
            service = BannerService(session)
            await service.update_review_message_info(
                application.id, review_message.id, review_thread_id
            )

        logger.info(f"已发送审核消息，申请ID: {application.id}")
        return True

    except Exception as e:
        logger.error(f"发送审核消息失败: {e}", exc_info=True)
        return False
