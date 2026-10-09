from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.thread_update_service import ThreadUpdateService
from core.tag_query import load_custom_tags
from core.viewer_flag_service import ViewerFlagService
from dto.thread_presentation_context import ThreadPresentationContext
from dto.thread_update_dto import ThreadUpdateDTO
from models import ThreadUpdate, TagBinding


class ThreadPresentationService:
    """批量加载完整作品响应需要的查看者状态和最新更新。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def load(
        self,
        user_id: int | None,
        threads: list[object],
    ) -> ThreadPresentationContext:
        """加载一批作品的展示上下文且不产生逐帖查询。"""
        pairs = [
            (int(getattr(thread, "thread_id")), int(getattr(thread, "author_id")))
            for thread in threads
        ]
        viewer_flags = await ViewerFlagService(self.session).get_flags(user_id, pairs)
        update_ids = {
            int(update_id)
            for thread in threads
            if (update_id := getattr(thread, "latest_update_id", None)) is not None
        }
        latest_updates: dict[int, ThreadUpdateDTO] = {}
        if update_ids:
            statement = select(ThreadUpdate).where(ThreadUpdate.id.in_(update_ids))
            records = list((await self.session.execute(statement)).scalars().all())
            latest_updates = {
                record.thread_id: ThreadUpdateService._to_dto(record)
                for record in records
            }
        native_tag_ids = {}
        if threads:
            bindings = (
                await self.session.execute(
                    select(TagBinding.target_id, TagBinding.tag_id).where(
                        TagBinding.target_type == "thread",
                        TagBinding.target_id.in_([getattr(t, "id") for t in threads]),
                        TagBinding.ended_at.is_(None),
                        TagBinding.binding_source == "discord_sync",
                    )
                )
            ).all()
            for target_id, tag_id in bindings:
                native_tag_ids.setdefault(target_id, set()).add(tag_id)
        return ThreadPresentationContext(
            native_tag_ids=native_tag_ids,
            viewer_flags=viewer_flags,
            latest_updates=latest_updates,
            custom_tags=await load_custom_tags(
                self.session, "thread", [getattr(t, "id") for t in threads]
            ),
        )
