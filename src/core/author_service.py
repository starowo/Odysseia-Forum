import logging
from typing import Dict, Any

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Author

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
        stmt = sqlite_insert(Author).values(author_data)
        update_stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=author_data,
        )

        try:
            await self.session.execute(update_stmt)
            await self.session.commit()
        except Exception as e:
            logger.error(
                f"更新作者 {author_data.get('id')} 信息到数据库时失败: {e}", exc_info=True
            )
            raise  # 重新抛出异常
