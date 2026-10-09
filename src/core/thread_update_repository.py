from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from models import ThreadUpdate


class ThreadUpdateRepository:
    """管理作品更新历史的单表数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, update_id: int) -> ThreadUpdate | None:
        """按逻辑主键获取更新。"""
        return await self.session.get(ThreadUpdate, update_id)

    async def get_by_message_id(self, message_id: int) -> ThreadUpdate | None:
        """按 Discord 来源消息 ID 获取更新。"""
        statement = select(ThreadUpdate).where(col(ThreadUpdate.message_id) == message_id)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_by_overview_message_id(
        self, overview_message_id: int
    ) -> ThreadUpdate | None:
        """按 Discord 概览消息 ID 获取更新。"""
        statement = select(ThreadUpdate).where(
            col(ThreadUpdate.overview_message_id) == overview_message_id
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_latest_for_thread(self, thread_id: int) -> ThreadUpdate | None:
        """获取作品最新的正式更新。"""
        statement = (
            select(ThreadUpdate)
            .where(col(ThreadUpdate.thread_id) == thread_id)
            .order_by(col(ThreadUpdate.published_at).desc(), col(ThreadUpdate.id).desc())
            .limit(1)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def add(self, update: ThreadUpdate) -> ThreadUpdate:
        """新增更新并取得数据库主键。"""
        self.session.add(update)
        await self.session.flush()
        return update

    async def delete(self, update: ThreadUpdate) -> None:
        """删除指定更新。"""
        await self.session.delete(update)
        await self.session.flush()

    async def delete_for_threads(self, thread_ids: list[int]) -> None:
        """批量删除作品的全部更新。"""
        if thread_ids:
            await self.session.execute(
                delete(ThreadUpdate).where(col(ThreadUpdate.thread_id).in_(thread_ids))
            )
