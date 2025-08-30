from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.thread import Thread


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
        stmt = select(Thread.thread_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
