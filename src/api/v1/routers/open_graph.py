from __future__ import annotations

import hmac
import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from dto.open_graph import (
    AuthorShareMetadataDTO,
    BooklistShareMetadataDTO,
    ThreadShareMetadataDTO,
)
from open_graph.author_open_graph_service import AuthorOpenGraphService
from open_graph.booklist_open_graph_service import BooklistOpenGraphService
from open_graph.image_resolver import OpenGraphImageResolver
from open_graph.metadata_cache import OpenGraphMetadataCache
from open_graph.reindex_queue import OpenGraphReindexQueue
from open_graph.thread_open_graph_service import ThreadOpenGraphService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/share-metadata", tags=["OG 内部接口"])

_service_token: str | None = None
_thread_open_graph_service: ThreadOpenGraphService | None = None
_author_open_graph_service: AuthorOpenGraphService | None = None
_booklist_open_graph_service: BooklistOpenGraphService | None = None


def configure_open_graph_router(
    *,
    session_factory: async_sessionmaker,
    redis: Redis,
    config: dict,
    abyss_config: dict | None = None,
) -> None:
    """注入三类 OG 服务的认证、缓存、图片和可见性配置。"""
    global _service_token
    global _thread_open_graph_service
    global _author_open_graph_service
    global _booklist_open_graph_service

    # 空令牌明确代表服务未配置，路由认证统一返回 503。
    raw_token = config.get("service_token")
    _service_token = (
        raw_token.strip() if isinstance(raw_token, str) and raw_token.strip() else None
    )

    # 数值配置在注入边界集中解析，非法值回退默认值而不拆分短辅助函数。
    raw_refresh_hours = config.get("refresh_before_expiry_hours", 1)
    try:
        refresh_before_expiry_hours = float(raw_refresh_hours)
        if (
            not math.isfinite(refresh_before_expiry_hours)
            or refresh_before_expiry_hours < 0
        ):
            refresh_before_expiry_hours = 1
    except (TypeError, ValueError):
        refresh_before_expiry_hours = 1

    raw_wait_timeout = config.get("sync_wait_timeout_seconds", 2)
    try:
        sync_wait_timeout_seconds = float(raw_wait_timeout)
        if (
            not math.isfinite(sync_wait_timeout_seconds)
            or sync_wait_timeout_seconds < 0
        ):
            sync_wait_timeout_seconds = 2
    except (TypeError, ValueError):
        sync_wait_timeout_seconds = 2

    raw_cache_ttl = config.get("cache_ttl_seconds", 600)
    try:
        cache_ttl_seconds = int(raw_cache_ttl)
        if cache_ttl_seconds <= 0:
            cache_ttl_seconds = 600
    except (TypeError, ValueError):
        cache_ttl_seconds = 600

    raw_max_jobs = config.get("max_async_refresh_jobs", 5)
    try:
        max_async_refresh_jobs = int(raw_max_jobs)
        if max_async_refresh_jobs < 0:
            max_async_refresh_jobs = 5
    except (TypeError, ValueError):
        max_async_refresh_jobs = 5

    # 深渊频道 ID 在启动时规范化，查询层只接收整数集合。
    excluded_channel_ids: set[int] = set()
    raw_channel_ids = (abyss_config or {}).get("channel_ids", [])
    if isinstance(raw_channel_ids, (list, tuple, set)):
        for channel_id in raw_channel_ids:
            try:
                excluded_channel_ids.add(int(channel_id))
            except (TypeError, ValueError):
                continue

    reindex_queue = OpenGraphReindexQueue(redis)
    image_resolver = OpenGraphImageResolver(
        reindex_queue=reindex_queue,
        refresh_before_expiry_seconds=refresh_before_expiry_hours * 3600,
        sync_wait_timeout_seconds=sync_wait_timeout_seconds,
        max_async_refresh_jobs=max_async_refresh_jobs,
    )
    metadata_cache = OpenGraphMetadataCache(redis, cache_ttl_seconds)
    _thread_open_graph_service = ThreadOpenGraphService(
        session_factory, image_resolver, metadata_cache, excluded_channel_ids
    )
    _author_open_graph_service = AuthorOpenGraphService(
        session_factory, image_resolver, metadata_cache, excluded_channel_ids
    )
    _booklist_open_graph_service = BooklistOpenGraphService(
        session_factory, image_resolver, metadata_cache, excluded_channel_ids
    )


async def require_open_graph_service_token(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> None:
    """使用常量时间比较校验内部接口的 Bearer 服务令牌。"""
    if _service_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Open Graph 服务未配置",
        )

    scheme, separator, supplied_token = (authorization or "").partition(" ")
    valid = (
        bool(separator)
        and scheme.lower() == "bearer"
        and hmac.compare_digest(supplied_token, _service_token)
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的服务令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/threads/{thread_id}",
    response_model=ThreadShareMetadataDTO,
    dependencies=[Depends(require_open_graph_service_token)],
    summary="获取帖子分享元数据",
)
async def get_thread_share_metadata(thread_id: int) -> ThreadShareMetadataDTO:
    """返回公开帖子的动态分享元数据。"""
    if _thread_open_graph_service is None:
        raise HTTPException(status_code=503, detail="Open Graph 服务尚未初始化")
    try:
        metadata = await _thread_open_graph_service.get_share_metadata(thread_id)
    except Exception:
        logger.error(
            "帖子 OG 元数据生成失败",
            extra={"resource_type": "thread", "resource_id": thread_id},
        )
        raise HTTPException(status_code=500, detail="分享元数据生成失败") from None
    if metadata is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    return metadata


@router.get(
    "/authors/{author_id}",
    response_model=AuthorShareMetadataDTO,
    dependencies=[Depends(require_open_graph_service_token)],
    summary="获取作者分享元数据",
)
async def get_author_share_metadata(author_id: int) -> AuthorShareMetadataDTO:
    """返回至少拥有一个公开作品的作者分享元数据。"""
    if _author_open_graph_service is None:
        raise HTTPException(status_code=503, detail="Open Graph 服务尚未初始化")
    try:
        metadata = await _author_open_graph_service.get_share_metadata(author_id)
    except Exception:
        logger.error(
            "作者 OG 元数据生成失败",
            extra={"resource_type": "author", "resource_id": author_id},
        )
        raise HTTPException(status_code=500, detail="分享元数据生成失败") from None
    if metadata is None:
        raise HTTPException(status_code=404, detail="作者不存在")
    return metadata


@router.get(
    "/booklists/{booklist_id}",
    response_model=BooklistShareMetadataDTO,
    dependencies=[Depends(require_open_graph_service_token)],
    summary="获取书单或赛事分享元数据",
)
async def get_booklist_share_metadata(
    booklist_id: int,
) -> BooklistShareMetadataDTO:
    """返回公开书单或赛事的动态分享元数据。"""
    if _booklist_open_graph_service is None:
        raise HTTPException(status_code=503, detail="Open Graph 服务尚未初始化")
    try:
        metadata = await _booklist_open_graph_service.get_share_metadata(booklist_id)
    except Exception:
        logger.error(
            "书单 OG 元数据生成失败",
            extra={"resource_type": "booklist", "resource_id": booklist_id},
        )
        raise HTTPException(status_code=500, detail="分享元数据生成失败") from None
    if metadata is None:
        raise HTTPException(status_code=404, detail="书单不存在")
    return metadata
