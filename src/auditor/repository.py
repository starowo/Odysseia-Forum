from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Thread


class AuditorRepository:
    """
    审计器的数据仓库，负责与数据库进行交互。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_thread_ids(self) -> list[int]:
        """
        从数据库中获取所有已索引帖子的 ID。

        Returns:
            一个包含所有帖子 ID 的列表。
        """
        stmt = select(Thread.thread_id)  # type: ignore
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_stale_threads(self, threshold: int) -> int:
        """
        物理删除那些 not_found_count 超过阈值的帖子记录。

        Returns:
            被删除的记录数量。
        """
        stmt = delete(Thread).where(Thread.not_found_count >= threshold)  # type: ignore
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
