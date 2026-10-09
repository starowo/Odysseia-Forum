import asyncio
import logging
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.booklist_item_repository import BooklistItemRepository
from core.booklist_publish_repository import BooklistPublishRepository
from core.booklist_repository import BooklistRepository
from core.booklist_sort_constants import DEFAULT_SORT_METHOD, DEFAULT_SORT_ORDER
from shared.database import AsyncSessionFactory
from shared.enum.booklist_publish_api_path import BooklistPublishApiPath
from shared.enum.booklist_publish_status import BooklistPublishStatus

logger = logging.getLogger(__name__)


class BooklistPublishService:
    """书单发布业务逻辑服务层，负责协调发布记录与书单发布 BOT API 调用"""

    def __init__(
        self,
        session: AsyncSession,
        base_url: str = "",
        api_key: str = "",
    ):
        self.session = session
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key
        self.publish_repo = BooklistPublishRepository(session)
        self.booklist_repo = BooklistRepository(session)

    @property
    def _publish_url(self) -> str:
        return f"{self.base_url}{BooklistPublishApiPath.PUBLISH.value}"

    @property
    def _unpublish_url(self) -> str:
        return f"{self.base_url}{BooklistPublishApiPath.UNPUBLISH.value}"

    def _ensure_configured(self) -> None:
        """若 base_url 未配置则抛出异常"""
        if not self.base_url:
            raise ValueError("书单发布服务未配置")

    async def publish(
        self,
        booklist_id: int,
        guild_id: int,
        thread_id: int,
        discord_user_id: int,
    ) -> None:
        """
        发布（或更新）书单到 Discord 讨论帖。

        1. Upsert BooklistPublish 记录
        2. 设置 Booklist.publish_status = PENDING
        3. commit -> 返回
        4. 后台 asyncio.create_task 调用 书单发布 API
        """
        self._ensure_configured()

        record = await self.publish_repo.upsert(
            booklist_id, guild_id, thread_id, discord_user_id
        )
        if record.id is None:  # pragma: no cover - 主键必定已生成
            raise RuntimeError(f"书单 {booklist_id} 发布记录缺少主键")

        # 后续提交会令 ORM 对象过期，先保存后台任务所需的请求凭证。
        record_id = record.id
        request_updated_at = record.updated_at

        await self.booklist_repo.set_publish_status(
            booklist_id, BooklistPublishStatus.PENDING.value
        )

        asyncio.create_task(
            self._do_call_friend_api(
                booklist_id=booklist_id,
                guild_id=guild_id,
                thread_id=thread_id,
                discord_user_id=discord_user_id,
                record_id=record_id,
                request_updated_at=request_updated_at,
            )
        )

    async def unpublish(self, booklist_id: int) -> None:
        """取消发布：完成本地处理后异步通知书单发布服务。"""
        # 删除前保存发布目标，避免提交后无法构造外部请求。
        record = await self.publish_repo.get_by_booklist(booklist_id)
        thread_url = None
        if record:
            thread_url = (
                f"https://discord.com/channels/{record.guild_id}/{record.thread_id}"
            )

        await self.publish_repo.delete_by_booklist(booklist_id)
        await self.booklist_repo.set_publish_status(
            booklist_id, BooklistPublishStatus.NONE.value
        )

        # 未发布的书单无需通知外部服务。
        if record:
            self.schedule_unpublish(booklist_id, thread_url)

    def schedule_unpublish(
        self, booklist_id: int, thread_url: str | None = None
    ) -> None:
        """创建外部取消发布后台任务，不阻塞本地主流程。"""
        if not self.base_url:
            logger.warning(
                "书单 %d 已完成本地取消发布，但书单发布服务未配置",
                booklist_id,
            )
            return

        asyncio.create_task(self._do_call_unpublish_api(booklist_id, thread_url))

    async def sync_published_booklist(self, booklist_id: int) -> None:
        """
        重新同步已发布书单的 embed。
        用于内容变更后的自动同步。若书单未发布或 base_url 未配置则静默跳过。
        """
        if not self.base_url:
            return

        record = await self.publish_repo.get_by_booklist(booklist_id)
        if not record:
            return

        guild_id = record.guild_id
        thread_id = record.thread_id
        discord_user_id = record.discord_user_id

        record = await self.publish_repo.upsert(
            booklist_id, guild_id, thread_id, discord_user_id
        )
        if record.id is None:  # pragma: no cover - 主键必定已生成
            raise RuntimeError(f"书单 {booklist_id} 发布记录缺少主键")

        # 后续提交会令 ORM 对象过期，先保存后台任务所需的请求凭证。
        record_id = record.id
        request_updated_at = record.updated_at

        await self.booklist_repo.set_publish_status(
            booklist_id, BooklistPublishStatus.PENDING.value
        )

        asyncio.create_task(
            self._do_call_friend_api(
                booklist_id=booklist_id,
                guild_id=guild_id,
                thread_id=thread_id,
                discord_user_id=discord_user_id,
                record_id=record_id,
                request_updated_at=request_updated_at,
            )
        )

    async def _do_call_friend_api(
        self,
        booklist_id: int,
        guild_id: int,
        thread_id: int,
        discord_user_id: int,
        record_id: int,
        request_updated_at: datetime,
    ) -> None:
        """
        后台任务：组装 payload、调用 书单发布 API、更新状态和 message_id/message_url。
        数据库读取、HTTP 调用、数据库写回分别使用独立生命周期，避免网络等待占用连接。
        """
        try:
            async with AsyncSessionFactory() as session:
                publish_repo = BooklistPublishRepository(session)
                if not await publish_repo.is_current_request(
                    booklist_id, record_id, request_updated_at
                ):
                    logger.info(
                        "跳过书单 %d 已过期的发布任务: thread_id=%d",
                        booklist_id,
                        thread_id,
                    )
                    return

                payload = await self._build_payload(
                    session, booklist_id, guild_id, thread_id, discord_user_id
                )

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._publish_url,
                    json=payload,
                    headers={"X-API-Key": self.api_key},
                    timeout=30.0,
                )
                resp.raise_for_status()
                result = resp.json()

            async with AsyncSessionFactory() as session:
                await self._on_api_success(
                    session,
                    booklist_id,
                    thread_id,
                    record_id,
                    request_updated_at,
                    result,
                )

            logger.info(
                "书单 %d 已成功发布到 thread_id=%d (updated=%s, message_id=%s)",
                booklist_id,
                thread_id,
                result.get("updated", False),
                result.get("message_id"),
            )

        except Exception:
            logger.warning(
                "书单 %d 发布到 书单发布 API 失败",
                booklist_id,
                exc_info=True,
            )
            try:
                async with AsyncSessionFactory() as session:
                    await self._on_api_failure(
                        session,
                        booklist_id,
                        thread_id,
                        record_id,
                        request_updated_at,
                    )
            except Exception:
                logger.error(
                    "更新书单 %d 发布失败状态时出错", booklist_id, exc_info=True
                )

    async def _do_call_unpublish_api(
        self, booklist_id: int, thread_url: str | None = None
    ) -> None:
        """后台调用取消发布 API，失败仅记录日志。"""
        payload: dict[str, int | str] = {"booklist_id": booklist_id}
        if thread_url is not None:
            payload["thread_url"] = thread_url

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._unpublish_url,
                    json=payload,
                    headers={"X-API-Key": self.api_key},
                    timeout=30.0,
                )
                resp.raise_for_status()
                result = resp.json()

            logger.info(
                "书单 %d 外部取消发布完成: requested=%s, deleted=%s",
                booklist_id,
                result.get("requested"),
                result.get("deleted"),
            )
        except Exception:
            logger.warning(
                "书单 %d 调用取消发布 API 失败",
                booklist_id,
                exc_info=True,
            )

    async def _build_payload(
        self,
        session: AsyncSession,
        booklist_id: int,
        guild_id: int,
        thread_id: int,
        discord_user_id: int,
    ) -> dict:
        """组装发给 书单发布 API 的 JSON payload"""
        repo = BooklistRepository(session)
        booklist = await repo.get_booklist(booklist_id)
        if not booklist:
            raise ValueError(f"书单 {booklist_id} 不存在")

        item_repo = BooklistItemRepository(session)
        sort_method = booklist.default_sort_method or DEFAULT_SORT_METHOD.value
        sort_order = booklist.default_sort_order or DEFAULT_SORT_ORDER.value
        items, _ = await item_repo.get_booklist_items_with_details(
            booklist_id=booklist_id,
            default_sort_method=sort_method,
            default_sort_order=sort_order,
            limit=1000,
            offset=0,
        )

        return {
            "booklist_id": booklist_id,
            "thread_url": f"https://discord.com/channels/{guild_id}/{thread_id}",
            "discord_user_id": str(discord_user_id),
            "title": booklist.title,
            "description": booklist.description or "",
            "cover_image_url": booklist.cover_image_url or "",
            "items": [
                {
                    "title": item.title,
                    "url": f"https://discord.com/channels/{item.guild_id}/{item.thread_id}",
                    "review": item.comment or "",
                }
                for item in items
            ],
        }

    async def _on_api_success(
        self,
        session: AsyncSession,
        booklist_id: int,
        thread_id: int,
        record_id: int,
        request_updated_at: datetime,
        result: dict,
    ) -> None:
        """书单发布 API 调用成功：更新 message_id/message_url 和状态"""
        message_id_str = result.get("message_id")
        message_id = int(message_id_str) if message_id_str else None
        message_url = result.get("message_url")

        publish_repo = BooklistPublishRepository(session)
        updated = await publish_repo.update_message_if_current(
            booklist_id,
            record_id,
            request_updated_at,
            message_id,
            message_url,
        )
        if not updated:
            logger.info(
                "忽略书单 %d 已过期的发布成功回调: thread_id=%d",
                booklist_id,
                thread_id,
            )
            return

        booklist_repo = BooklistRepository(session)
        await booklist_repo.set_publish_status(
            booklist_id, BooklistPublishStatus.SUCCESS.value, commit=False
        )
        await session.commit()

    async def _on_api_failure(
        self,
        session: AsyncSession,
        booklist_id: int,
        thread_id: int,
        record_id: int,
        request_updated_at: datetime,
    ) -> None:
        """书单发布 API 调用失败：标记 publish_status = FAILED"""
        publish_repo = BooklistPublishRepository(session)
        if not await publish_repo.lock_current_request(
            booklist_id, record_id, request_updated_at
        ):
            logger.info(
                "忽略书单 %d 已过期的发布失败回调: thread_id=%d",
                booklist_id,
                thread_id,
            )
            return

        booklist_repo = BooklistRepository(session)
        await booklist_repo.set_publish_status(
            booklist_id, BooklistPublishStatus.FAILED.value, commit=False
        )
        await session.commit()
