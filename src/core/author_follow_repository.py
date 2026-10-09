from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Author, AuthorFollow
from shared.time_utils import utc_now


class AuthorFollowRepository:
    """管理作者关注关系的单表写入与关联读取。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_active(
        self,
        user_id: int,
        author_id: int,
        active: bool,
    ) -> AuthorFollow | None:
        """幂等设置作者关注状态。"""
        statement = select(AuthorFollow).where(
            AuthorFollow.user_id == user_id,
            AuthorFollow.author_id == author_id,
        )
        relation = (await self.session.execute(statement)).scalar_one_or_none()
        if relation is None:
            if not active:
                return None
            relation = AuthorFollow(user_id=user_id, author_id=author_id)
            self.session.add(relation)
            await self.session.flush()
            return relation

        if active and not relation.active_flag:
            relation.followed_at = utc_now()
        relation.active_flag = active
        self.session.add(relation)
        await self.session.flush()
        return relation

    async def list_for_user(
        self,
        user_id: int,
        active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[AuthorFollow, Author]], int]:
        """分页返回用户关注的作者及作者资料。"""
        conditions = [AuthorFollow.user_id == user_id]
        if active is not None:
            conditions.append(AuthorFollow.active_flag == active)
        statement = (
            select(AuthorFollow, Author)
            .join(Author, Author.id == AuthorFollow.author_id)
            .where(*conditions)
            .order_by(AuthorFollow.followed_at.desc(), AuthorFollow.id.desc())
            .limit(limit)
            .offset(offset)
        )
        count_statement = (
            select(func.count()).select_from(AuthorFollow).where(*conditions)
        )
        rows = list((await self.session.execute(statement)).all())
        total = int((await self.session.execute(count_statement)).scalar_one())
        return rows, total
