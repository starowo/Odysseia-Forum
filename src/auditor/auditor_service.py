from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Thread
from core.thread_deletion_service import ThreadDeletionService


class AuditorService:
    """
    审计器的处理逻辑，负责与数据库进行交互。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_thread_ids_batch(
        self, cursor: int, batch_size: int
    ) -> list[tuple[int, int]]:
        """
        使用 keyset 分页，从数据库中获取一批帖子的 (id, thread_id)。

        以自增主键 ``id`` 作为游标，保证严格单调递增，
        新插入的行永远在游标前方，不会遗漏。

        Args:
            cursor: 上一批最后一个 id（起始传 0）。
            batch_size: 本批最多返回的行数。

        Returns:
            [(id, thread_id), ...] 列表，按 id 升序排列。
        """
        stmt = (
            select(Thread.id, Thread.thread_id)  # type: ignore
            .where(Thread.id > cursor)  # type: ignore
            .order_by(Thread.id)
            .limit(batch_size)
        )
        result = await self.session.execute(stmt)
        return list(result.all())  # type: ignore[return-value]

    async def delete_stale_threads(self, threshold: int) -> int:
        """
        物理删除那些 not_found_count 超过阈值的帖子记录。

        Returns:
            被删除的记录数量。
        """
        deleted_count = await ThreadDeletionService(self.session).delete_stale(
            threshold
        )
        await self.session.commit()
        return deleted_count
