from core.tag_binding_repository import TagBindingRepository
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    BannerApplication,
    BannerCarousel,
    BannerWaitlist,
    BooklistItem,
    Notification,
    Thread,
    ThreadFollow,
    ThreadUpdate,
    UserCollection,
    UserUpdatePreference,
)
from shared.enum import CollectionType, TargetType

logger = logging.getLogger(__name__)


class ThreadDeletionService:
    """显式清理逻辑 ID 关联后删除索引作品。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_thread(self, thread_id: int) -> int:
        """删除单个作品及全部逻辑关联数据。"""
        return await self.delete_threads([thread_id])

    async def delete_channel(self, channel_id: int) -> int:
        """删除指定索引频道下的全部作品与逻辑关联。"""
        statement = select(Thread.thread_id).where(Thread.channel_id == channel_id)
        thread_ids = list((await self.session.execute(statement)).scalars().all())
        return await self.delete_threads(thread_ids)

    async def delete_stale(self, threshold: int) -> int:
        """删除连续拉取失败次数达到阈值的作品。"""
        statement = select(Thread.thread_id).where(Thread.not_found_count >= threshold)
        thread_ids = list((await self.session.execute(statement)).scalars().all())
        return await self.delete_threads(thread_ids)

    async def delete_threads(self, thread_ids: list[int]) -> int:
        """批量清理作品，所有关联均为显式逻辑关联。"""
        unique_ids = sorted(set(thread_ids))
        if not unique_ids:
            return 0
        internal_statement = (
            select(Thread.id).where(Thread.thread_id.in_(unique_ids)).with_for_update()
        )
        internal_ids = list(
            (await self.session.execute(internal_statement)).scalars().all()
        )

        await self.session.execute(
            delete(Notification).where(Notification.thread_id.in_(unique_ids))
        )
        await self.session.execute(
            delete(ThreadUpdate).where(ThreadUpdate.thread_id.in_(unique_ids))
        )
        await self.session.execute(
            delete(ThreadFollow).where(ThreadFollow.thread_id.in_(unique_ids))
        )
        await self.session.execute(
            delete(UserUpdatePreference).where(
                UserUpdatePreference.thread_id.in_(unique_ids)
            )
        )
        await self.session.execute(
            delete(BooklistItem).where(BooklistItem.thread_id.in_(unique_ids))
        )
        await self.session.execute(
            delete(UserCollection).where(
                UserCollection.target_type == CollectionType.THREAD.value,
                UserCollection.target_id.in_(unique_ids),
            )
        )
        for banner_model in (BannerApplication, BannerCarousel, BannerWaitlist):
            await self.session.execute(
                delete(banner_model).where(
                    banner_model.target_type == TargetType.THREAD.value,
                    banner_model.thread_id.in_(unique_ids),
                )
            )
        await TagBindingRepository(self.session).delete_targets("thread", internal_ids)
        result = await self.session.execute(
            delete(Thread).where(Thread.thread_id.in_(unique_ids))
        )
        return int(result.rowcount or 0)
