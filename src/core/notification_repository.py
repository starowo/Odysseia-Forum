from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import Notification
from shared.time_utils import utc_now


class NotificationRepository:
    """管理动态通知的单表数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(
        self,
        user_id: int,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int, int]:
        """分页读取通知并同时返回总数与未读数。"""
        conditions = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.read_at.is_(None))
        statement = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        total_statement = (
            select(func.count()).select_from(Notification).where(*conditions)
        )
        unread_statement = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        rows = list((await self.session.execute(statement)).scalars().all())
        total = int((await self.session.execute(total_statement)).scalar_one())
        unread = int((await self.session.execute(unread_statement)).scalar_one())
        return rows, total, unread

    async def unread_count(self, user_id: int) -> int:
        """获取用户动态通知未读数。"""
        statement = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        return int((await self.session.execute(statement)).scalar_one())

    async def mark_thread_read(self, user_id: int, thread_id: int) -> int:
        """将用户在某作品下的全部未读动态标为已读。"""
        statement = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.thread_id == thread_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=utc_now())
        )
        result = await self.session.execute(statement)
        return int(result.rowcount or 0)

    async def mark_one_read(self, user_id: int, notification_id: int) -> int:
        """仅标记当前用户拥有的单条通知。"""
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=utc_now())
        )
        return int(result.rowcount or 0)

    async def mark_all_read(self, user_id: int) -> int:
        """将用户的全部未读动态标为已读。"""
        statement = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=utc_now())
        )
        result = await self.session.execute(statement)
        return int(result.rowcount or 0)

    async def delete_for_event(self, event_type: str, event_source_id: int) -> None:
        """删除指定业务事件产生的全部通知。"""
        await self.session.execute(
            delete(Notification).where(
                Notification.event_type == event_type,
                Notification.event_source_id == event_source_id,
            )
        )

    async def delete_for_threads(self, thread_ids: list[int]) -> None:
        """批量删除作品关联的全部通知。"""
        if thread_ids:
            await self.session.execute(
                delete(Notification).where(Notification.thread_id.in_(thread_ids))
            )
