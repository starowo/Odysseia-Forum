from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas.booklist import BooklistItemDetail
from api.v1.schemas.search import LatestUpdate
from core.thread_presentation_service import ThreadPresentationService
from core.thread_repository import ThreadRepository


class BooklistItemEnricher:
    """批量补充书单完整作品条目的查看者状态和最新更新。"""

    @staticmethod
    async def enrich(
        session: AsyncSession,
        user_id: int | None,
        items: list[BooklistItemDetail],
    ) -> None:
        """原地补充一批书单条目且不产生逐帖查询。"""
        if not items:
            return
        thread_ids = [item.thread_id for item in items]
        threads = await ThreadRepository(session).get_threads_by_ids_with_tags(
            thread_ids
        )
        thread_map = {thread.thread_id: thread for thread in threads}
        context = await ThreadPresentationService(session).load(user_id, threads)
        for item in items:
            item.viewer_flags = context.viewer_flags.for_thread(item.thread_id)
            item.collected_flag = "collected" in item.viewer_flags
            update = context.latest_updates.get(item.thread_id)
            thread = thread_map.get(item.thread_id)
            if update is None or thread is None:
                item.latest_update = None
                continue
            message_link = None
            if update.message_id is not None:
                message_link = (
                    f"https://discord.com/channels/{thread.guild_id}/"
                    f"{thread.thread_id}/{update.message_id}"
                )
            item.latest_update = LatestUpdate(
                id=update.id,
                description=update.description,
                version=update.version,
                message_link=message_link,
                source_message_at=update.source_message_at,
                published_at=update.published_at,
            )
