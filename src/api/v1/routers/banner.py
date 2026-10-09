"""Banner申请API路由"""

import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.v1.dependencies.security import get_current_user, require_auth
from api.v1.schemas.banner import (
    BannerApplicationRequest,
    BannerApplicationResponse,
    BannerItem,
)
from api.v1.utils.preferences_utils import get_user_preferences_cached
from banner.banner_service import BannerService
from banner.channel_sync import ChannelSyncService
from core.tag_cache_service import TagCacheService
from core.banner_thread_visibility_service import BannerThreadVisibilityService
from core.banner_title_filter_repository import BannerTitleFilterRepository
from core.thread_repository import ThreadRepository
from models.channel import Channel
from shared.enum import TargetType
from shared.redis_client import RedisManager
from shared.thread_link_parser import ThreadLinkParser

logger = logging.getLogger(__name__)

# 全局变量，将在应用启动时注入
async_session_factory: async_sessionmaker | None = None
banner_config: dict | None = None
main_guild_id: int = 0
bot_token: str = ""
tag_cache_service_instance: TagCacheService | None = None
channel_mappings_config: Dict[int, List[Dict]] = {}


def _normalize_banner_channel_ids(
    channel_ids: list[int | str] | None,
    channel_id: int | str | None,
) -> list[int]:
    """合并新旧频道参数并稳定去重为整数 ID 列表。"""
    raw_channel_ids = list(channel_ids or [])
    if channel_id is not None:
        raw_channel_ids.append(channel_id)

    normalized_channel_ids: list[int] = []
    seen_channel_ids: set[int] = set()
    for raw_channel_id in raw_channel_ids:
        try:
            normalized_channel_id = int(raw_channel_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的频道ID格式: {raw_channel_id}",
            )
        if normalized_channel_id in seen_channel_ids:
            continue
        seen_channel_ids.add(normalized_channel_id)
        normalized_channel_ids.append(normalized_channel_id)

    return normalized_channel_ids


router = APIRouter(
    prefix="/banner", tags=["Banner管理"], dependencies=[Depends(require_auth)]
)


@router.post(
    "/apply", response_model=BannerApplicationResponse, summary="提交Banner申请"
)
async def apply_banner(
    request: BannerApplicationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """提交Banner展示位申请。

    支持 Discord 跳转链接或纯数字 ID。
    传入纯数字 ID 时自动使用主服务器 ID 拼接。
    """
    if not async_session_factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务尚未初始化",
        )

    # 解析链接
    parsed = ThreadLinkParser.parse_thread_link(request.thread_link, main_guild_id)
    if parsed is None:
        return BannerApplicationResponse(
            success=False,
            message="thread_link 格式无效，请提供 Discord 跳转链接或纯数字ID",
        )
    guild_id, target_id = parsed

    user_id = int(current_user.get("id", 0))

    # 创建 ChannelSyncService（如果有 bot_token）
    channel_sync = None
    if bot_token:
        channel_sync = ChannelSyncService(bot_token)

    try:
        async with async_session_factory() as session:
            service = BannerService(session, channel_sync=channel_sync)
            result = await service.validate_and_create_application(
                target_id=target_id,
                guild_id=guild_id,
                applicant_id=user_id,
                cover_image_url=request.cover_image_url,
                target_scope=request.target_scope,
            )

            if not result.success:
                return BannerApplicationResponse(success=False, message=result.message)

            application = result.application

            # 将审核消息放入 Redis 队列，由 Bot 进程消费发送
            if banner_config and application:
                try:
                    redis = RedisManager.get_client()
                    await redis.lpush(  # type: ignore[return-type]
                        "banner:review:queue",
                        json.dumps({"application_id": application.id}),
                    )
                except Exception:
                    logger.warning(
                        f"审核消息入队失败，但申请已创建。申请ID: {application.id}",
                        exc_info=True,
                    )
            else:
                logger.warning("Banner配置未初始化，跳过审核消息入队")

            return BannerApplicationResponse(
                success=True,
                message=result.message,
                application_id=application.id if application else None,
            )

    except Exception as e:
        logger.error(f"处理Banner申请时出错: {e}", exc_info=True)
        return BannerApplicationResponse(
            success=False, message=f"提交申请时出错: {str(e)}"
        )


@router.get(
    "/active",
    response_model=List[BannerItem],
    summary="获取当前活跃的Banner列表",
)
async def get_active_banners(
    channel_ids: list[int | str] | None = Query(
        default=None,
        description="频道ID列表，可重复传入；优先于偏好频道。不传时使用偏好频道，偏好为空则返回全部；始终合并全局Banner",
    ),
    channel_id: int | str | None = Query(
        default=None,
        description="兼容旧调用的单个频道ID；传入后合并到channel_ids",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取当前活跃的Banner轮播列表。"""
    if not async_session_factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务尚未初始化",
        )

    effective_channel_ids = _normalize_banner_channel_ids(channel_ids, channel_id)

    try:
        async with async_session_factory() as session:
            service = BannerService(session)
            # 加载用户搜索偏好，失败时仅跳过偏好项。
            user_id = int(current_user.get("id", 0)) if current_user else 0
            prefs = None
            redis_client = None
            if user_id:
                try:
                    redis_client = RedisManager.get_client()
                    prefs = await get_user_preferences_cached(
                        redis_client, async_session_factory, user_id, main_guild_id
                    )
                except Exception:
                    logger.warning("读取用户偏好失败，跳过偏好筛选", exc_info=True)

            # 显式参数优先；未传参数时使用偏好频道，均为空则查询全部。
            if not effective_channel_ids and prefs and prefs.preferred_channels:
                effective_channel_ids = list(dict.fromkeys(prefs.preferred_channels))
            banners = await service.get_active_banners(
                channel_ids=effective_channel_ids,
                all_channels=not effective_channel_ids,
            )

            # 频道目标按轮播标题快照过滤，避免同目标不同范围的标题互相影响。
            excluded_banner_ids: set[int] = set()
            if prefs and prefs.exclude_keywords:
                excluded_banner_ids = await BannerTitleFilterRepository(session).get_excluded_ids(
                    titles={
                        banner.id: banner.title for banner in banners
                        if banner.target_type == TargetType.CHANNEL.value and banner.id is not None
                    },
                    exclude_keywords=prefs.exclude_keywords,
                    exemption_markers=prefs.exclude_keyword_exemption_markers,
                    redis_client=redis_client,
                )
            banners = [banner for banner in banners if banner.id not in excluded_banner_ids]

            # 批量筛选帖子 Banner，并同时取得其服务器 ID。
            thread_tids = [
                banner.thread_id
                for banner in banners
                if banner.target_type == TargetType.THREAD.value
            ]
            guild_map: dict[int, int] = {}
            thumbnail_map: dict[int, str | None] = {}
            allowed_thread_guilds: dict[int, int] = {}
            if thread_tids:
                if tag_cache_service_instance is None:
                    raise RuntimeError("Banner TAG 缓存服务尚未初始化")

                allowed_thread_guilds = await BannerThreadVisibilityService(
                    session=session,
                    tag_cache_service=tag_cache_service_instance,
                ).get_visible_thread_guilds(
                    thread_ids=thread_tids,
                    prefs=prefs,
                    channel_mappings_config=channel_mappings_config,
                    redis_client=redis_client,
                )
                guild_map.update(allowed_thread_guilds)
                indexed_threads = await ThreadRepository(
                    session
                ).get_threads_by_ids_with_tags(thread_tids)
                thumbnail_map = {
                    thread.thread_id: (
                        thread.thumbnail_urls[0] if thread.thumbnail_urls else None
                    )
                    for thread in indexed_threads
                }

            # 批量查询频道 Banner 对应的服务器 ID。
            channel_cids = [
                banner.thread_id
                for banner in banners
                if banner.target_type == TargetType.CHANNEL.value
            ]
            if channel_cids:
                channel_rows = await session.execute(
                    select(Channel.channel_id, Channel.guild_id).where(  # type: ignore[arg-type]
                        Channel.channel_id.in_(channel_cids)  # type: ignore[arg-type]
                    )
                )
                guild_map.update({cid: gid for cid, gid in channel_rows.all()})

            # 按轮播记录 ID 顺序返回，不从等待列表为偏好过滤补位。
            return [
                BannerItem(
                    thread_id=banner.thread_id,
                    title=banner.title,
                    cover_image_url=(
                        banner.cover_image_url
                        if banner.cover_image_url
                        else thumbnail_map.get(banner.thread_id)
                    ),
                    channel_id=banner.channel_id if banner.channel_id else 0,
                    guild_id=guild_map.get(banner.thread_id, 0),
                    target_type=banner.target_type,
                    start_time=banner.start_time,
                    end_time=banner.end_time,
                )
                for banner in banners
                if banner.target_type != TargetType.THREAD.value
                or banner.thread_id in allowed_thread_guilds
            ]
    except Exception as e:
        logger.error(f"获取Banner列表时出错: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取Banner列表时出错",
        )
