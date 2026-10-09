import logging
from typing import Dict, Any, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Author, Thread
from dto.open_graph import AuthorShareQueryDTO

logger = logging.getLogger(__name__)


class AuthorRepository:
    """
    负责 Author 模型在数据库中的持久化操作。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_author(self, author_data: Dict[str, Any]) -> None:
        """
        使用 INSERT ... ON CONFLICT DO UPDATE (Upsert) 更新或插入作者信息。

        Args:
            author_data: 包含作者信息的字典，键应与 Author 模型字段匹配。
        """
        stmt = pg_insert(Author).values(author_data)
        update_stmt = stmt.on_conflict_do_update(
            constraint="author_pkey",
            set_=author_data,
        )

        try:
            await self.session.execute(update_stmt)
            await self.session.commit()
        except Exception as e:
            logger.error(
                f"更新作者 {author_data.get('id')} 信息到数据库时失败: {e}",
                exc_info=True,
            )
            raise  # 重新抛出异常

    async def get_author(self, author_id: int) -> Optional[Author]:
        """根据作者ID获取作者实体信息。"""
        statement = select(Author).where(Author.id == author_id)  # type: ignore
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_open_graph_author(self, author_id: int) -> AuthorShareQueryDTO | None:
        """查询作者分享所需标量并在 Session 内转换为 DTO。"""
        statement = select(
            Author.display_name,
            Author.avatar_url,
            Author.last_updated,
        ).where(Author.id == author_id)
        row = (await self.session.execute(statement)).first()
        if row is None:
            return None
        return AuthorShareQueryDTO(
            display_name=row.display_name,
            avatar_url=row.avatar_url,
            last_updated=row.last_updated,
        )

    async def get_authors_by_ids(self, author_ids: List[int]) -> Sequence[Author]:
        """批量获取作者信息"""
        if not author_ids:
            return []
        statement = select(Author).where(Author.id.in_(author_ids))  # type: ignore
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_author_stats(self, author_id: int) -> dict:
        """获取指定作者的发帖数、总反应数和总回复数统计。"""
        # 仅统计未被标记为软删除的帖子 (not_found_count == 0)
        statement = select(
            func.count(Thread.id).label("thread_count"),  # type: ignore
            func.coalesce(func.sum(Thread.reaction_count), 0).label("reaction_count"),
            func.coalesce(func.sum(Thread.reply_count), 0).label("reply_count"),
        ).where(Thread.author_id == author_id, Thread.not_found_count == 0)  # type: ignore

        result = await self.session.execute(statement)
        row = result.first()

        if row:
            return {
                "thread_count": row.thread_count,
                "reaction_count": row.reaction_count,
                "reply_count": row.reply_count,
            }
        return {"thread_count": 0, "reaction_count": 0, "reply_count": 0}
