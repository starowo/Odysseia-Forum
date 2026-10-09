from __future__ import annotations

import logging
from typing import Any, List, Optional, Union

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.v1.dependencies.security import require_auth
from core.thread_repository import ThreadRepository
from shared.image_url_utils import extract_message_image_urls

DISCORD_API_BASE = "https://discord.com/api/v10"

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/fetch-images",
    tags=["图片刷新"],
    dependencies=[Depends(require_auth)],
)

_async_session_factory: Optional[async_sessionmaker] = None
_bot_token: Optional[str] = None
_guild_id: Optional[str] = None


class FetchImageItem(BaseModel):
    thread_id: Union[int, str] = Field(
        ..., description="Discord Thread ID (也是首楼消息ID)"
    )
    channel_id: Optional[Union[int, str]] = Field(
        default=None,
        description="帖子所属频道ID，可选，仅用于调试记录，支持数字或字符串",
    )

    @field_validator("thread_id", "channel_id", mode="before")
    @classmethod
    def convert_ids_to_int(cls, v: Any) -> Any:
        """
        在 Pydantic 校验前，将字符串形式的 Discord ID 转换为 int。
        """
        if v is None:
            return v

        if isinstance(v, str) and v.isdigit():
            return int(v)

        return v


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
        logger.error(f"获取 Discord 消息失败 (thread_id={item.thread_id}): {exc}")
        response_item.error = f"httpx_error: {exc}"
        return response_item

    if resp.status_code == status.HTTP_404_NOT_FOUND:
        response_item.error = "not_found"
        return response_item

    if resp.status_code != status.HTTP_200_OK:
        logger.debug(
            f"Discord API 返回非 200 状态码 (thread_id={item.thread_id}): {resp.status_code}"
        )
        response_item.error = f"http_status_{resp.status_code}"
        return response_item

    message_payload = resp.json()
    thumbnail_urls = extract_message_image_urls(
        attachments=message_payload.get("attachments") or [],
        embeds=message_payload.get("embeds") or [],
        content=message_payload.get("content") or "",
    )
    response_item.thumbnail_urls = thumbnail_urls
    response_item.updated = await _persist_thumbnail(item.thread_id, thumbnail_urls)  # type: ignore
    return response_item


async def _persist_thumbnail(thread_id: int, thumbnail_urls: List[str]) -> bool:
    assert _async_session_factory is not None  # 为类型检查器准备
    try:
        async with _async_session_factory() as session:
            repo = ThreadRepository(session)
            return await repo.update_thread_thumbnail_urls(thread_id, thumbnail_urls)
    except Exception as e:
        logger.error(f"持久化缩略图失败 (thread_id={thread_id}): {e}", exc_info=True)
        return False
