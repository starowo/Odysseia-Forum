from __future__ import annotations

import re
from typing import Any, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..dependencies.security import require_auth
from shared.models.thread import Thread

DISCORD_API_BASE = "https://discord.com/api/v10"
IMAGE_URL_REGEX = re.compile(
    r"https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)", re.IGNORECASE
)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

router = APIRouter(
    prefix="/fetch-images",
    tags=["图片刷新"],
    dependencies=[Depends(require_auth)],
)

_async_session_factory: Optional[async_sessionmaker] = None
_bot_token: Optional[str] = None
_guild_id: Optional[str] = None


class FetchImageItem(BaseModel):
    thread_id: int = Field(..., description="Discord Thread ID (也是首楼消息ID)")
    channel_id: Optional[int] = Field(
        default=None, description="帖子所属频道ID，可选，仅用于调试记录"
    )


class FetchImageRequest(BaseModel):
    items: List[FetchImageItem]


class FetchImageResponseItem(BaseModel):
    thread_id: str
    thumbnail_urls: List[str] = Field(default_factory=list)
    updated: bool = False
    error: Optional[str] = None


class FetchImageResponse(BaseModel):
    results: List[FetchImageResponseItem]


def configure_fetch_images_router(
    *,
    session_factory: async_sessionmaker,
    bot_token: Optional[str],
    guild_id: Optional[str],
) -> None:
    """
    由 bot_main 在启动时调用，注入共享依赖。
    """
    global _async_session_factory, _bot_token, _guild_id
    _async_session_factory = session_factory
    _bot_token = bot_token
    _guild_id = guild_id


@router.post("/", response_model=FetchImageResponse, summary="批量刷新帖子封面")
async def refresh_thread_thumbnails(payload: FetchImageRequest) -> FetchImageResponse:
    """
    接收前端上报的失效封面列表，使用 Discord Bot Token 拉取最新的首楼消息，
    提取图片链接后更新数据库并返回。
    """
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请求列表不能为空",
        )

    if not _async_session_factory or not _bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="图片刷新服务尚未初始化",
        )

    results: List[FetchImageResponseItem] = []

    headers = {
        "Authorization": f"Bot {_bot_token}",
        "User-Agent": "OdysseiaBot (fetch-images)",
    }

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        for item in payload.items:
            response_item = await _process_single_item(client, item)
            results.append(response_item)

    return FetchImageResponse(results=results)


async def _process_single_item(
    client: httpx.AsyncClient, item: FetchImageItem
) -> FetchImageResponseItem:
    url = f"{DISCORD_API_BASE}/channels/{item.thread_id}/messages/{item.thread_id}"
    response_item = FetchImageResponseItem(thread_id=str(item.thread_id))

    try:
        resp = await client.get(url)
    except httpx.HTTPError as exc:  # pragma: no cover - 网络错误情况下的日志
        response_item.error = f"httpx_error: {exc}"
        return response_item

    if resp.status_code == status.HTTP_404_NOT_FOUND:
        response_item.error = "not_found"
        return response_item

    if resp.status_code != status.HTTP_200_OK:
        response_item.error = f"http_status_{resp.status_code}"
        return response_item

    message_payload = resp.json()
    thumbnail_urls = _extract_thumbnail_urls(message_payload)

    if not thumbnail_urls:
        response_item.error = "no_image_found"
        return response_item

    response_item.thumbnail_urls = thumbnail_urls
    response_item.updated = await _persist_thumbnail(item.thread_id, thumbnail_urls)
    return response_item


def _is_image_attachment(attachment: dict[str, Any]) -> bool:
    content_type = (attachment.get("content_type") or "").lower()
    filename = (attachment.get("filename") or "").lower()
    return content_type.startswith("image/") or filename.endswith(IMAGE_EXTENSIONS)


def _extract_thumbnail_urls(message_payload: dict[str, Any]) -> List[str]:
    urls: List[str] = []

    attachments = message_payload.get("attachments") or []
    for attachment in attachments:
        if _is_image_attachment(attachment):
            url = attachment.get("proxy_url") or attachment.get("url")
            if url:
                urls.append(url)

    embeds = message_payload.get("embeds") or []
    for embed in embeds:
        image_block = embed.get("image") or embed.get("thumbnail")
        if image_block:
            url = image_block.get("proxy_url") or image_block.get("url")
            if url:
                urls.append(url)

    content = message_payload.get("content") or ""
    if content:
        urls.extend(re.findall(IMAGE_URL_REGEX, content))

    deduped: List[str] = []
    seen: set[str] = set()
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            deduped.append(url)

    return deduped


async def _persist_thumbnail(thread_id: int, thumbnail_urls: List[str]) -> bool:
    assert _async_session_factory is not None  # 为类型检查器准备
    async with _async_session_factory() as session:
        stmt = (
            update(Thread)
            .where(Thread.thread_id == thread_id)  # type: ignore[arg-type]
            .values(thumbnail_urls=thumbnail_urls)
        )
        result = await session.execute(stmt)
        await session.commit()
        return bool(result.rowcount)
