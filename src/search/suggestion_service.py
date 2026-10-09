from models.tag_alias import TagAlias
import re
from typing import List, Optional

from sqlalchemy import String, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import or_, select

from dto.search import SuggestionResultDTO
from models import Author, Booklist, Tag, Thread


class SuggestionService:
    """提供全局搜索的联想建议服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_suggestions(
        self,
        keyword: str,
        limit: int = 3,
        current_user_id: Optional[int] = None,
        exclude_authors: Optional[List[int]] = None,
        exclude_keywords: Optional[str] = None,
        exclude_tags: Optional[List[str]] = None,
        include_abyss_tags: bool = False,
    ) -> SuggestionResultDTO:
        keyword = keyword.strip()
        if not keyword:
            return SuggestionResultDTO()

        search_pattern = f"%{keyword}%"
        is_numeric = keyword.isdigit()

        # --- 作者查询 ---
        author_stmt = select(Author)
        if is_numeric:
            author_stmt = author_stmt.where(
                or_(
                    func.cast(Author.id, String).like(search_pattern),  # type: ignore[arg-type]
                    Author.name.like(search_pattern),  # type: ignore[attr-defined]
                    Author.display_name.like(search_pattern),  # type: ignore[attr-defined]
                )
            )
        else:
            author_stmt = author_stmt.where(
                or_(
                    Author.name.like(search_pattern),  # type: ignore[attr-defined]
                    Author.display_name.like(search_pattern),  # type: ignore[attr-defined]
                )
            )
        if exclude_authors:
            author_stmt = author_stmt.where(Author.id.notin_(exclude_authors))  # type: ignore[attr-defined]
        author_stmt = author_stmt.limit(limit)

        # --- 帖子查询 ---
        thread_stmt = select(Thread).where(
            Thread.not_found_count == 0,
            Thread.show_flag,  # type: ignore[attr-defined]
        )
        if is_numeric:
            thread_stmt = thread_stmt.where(
                or_(
                    func.cast(Thread.thread_id, String).like(search_pattern),  # type: ignore[arg-type]
                    Thread.title.like(search_pattern),  # type: ignore[attr-defined]
                )
            )
        else:
            thread_stmt = thread_stmt.where(Thread.title.like(search_pattern))  # type: ignore[attr-defined]

        if exclude_authors:
            thread_stmt = thread_stmt.where(Thread.author_id.notin_(exclude_authors))  # type: ignore[attr-defined]

        if exclude_keywords and exclude_keywords.strip():
            for kw in re.split(r"[,，/\s]+", exclude_keywords.strip()):
                thread_stmt = thread_stmt.where(
                    ~Thread.title.like(f"%{kw}%")  # type: ignore[attr-defined]
                )

        if exclude_tags:
            for tag_name in exclude_tags:
                thread_stmt = thread_stmt.where(
                    ~Thread.tags.any(Tag.name == tag_name)  # type: ignore[attr-defined]
                )

        thread_stmt = thread_stmt.order_by(Thread.last_active_at.desc()).limit(limit)  # type: ignore[attr-defined]

        # --- 书单查询 ---
        booklist_stmt = select(Booklist)
        visibility_cond = Booklist.is_public  # type: ignore[attr-defined]
        if current_user_id:
            visibility_cond = or_(
                visibility_cond,
                Booklist.owner_id == current_user_id,  # type: ignore[attr-defined]
            )
        booklist_stmt = booklist_stmt.where(visibility_cond)
        if is_numeric:
            booklist_stmt = booklist_stmt.where(
                or_(
                    func.cast(Booklist.id, String).like(search_pattern),  # type: ignore[arg-type]
                    Booklist.title.like(search_pattern),  # type: ignore[attr-defined]
                    Booklist.description.like(search_pattern),  # type: ignore[attr-defined]
                )
            )
        else:
            booklist_stmt = booklist_stmt.where(
                or_(
                    Booklist.title.like(search_pattern),  # type: ignore[attr-defined]
                    Booklist.description.like(search_pattern),  # type: ignore[attr-defined]
                )
            )
        booklist_stmt = booklist_stmt.order_by(Booklist.view_count.desc()).limit(limit)  # type: ignore[attr-defined]

        escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        tag_stmt = select(Tag).where(
            Tag.deleted_at.is_(None),
            Tag.enabled.is_(True),
            or_(
                Tag.name.ilike(pattern),
                Tag.id.in_(select(TagAlias.tag_id).where(TagAlias.name.ilike(pattern))),
            ),
        )
        if not include_abyss_tags:
            tag_stmt = tag_stmt.where(Tag.is_abyss.is_(False))
        tag_res = await self.session.execute(
            tag_stmt.order_by(Tag.name, Tag.category, Tag.id).limit(limit)
        )
        author_res = await self.session.execute(author_stmt)
        thread_res = await self.session.execute(thread_stmt)
        booklist_res = await self.session.execute(booklist_stmt)

        return SuggestionResultDTO(
            tags=list(tag_res.scalars().all()),
            authors=list(author_res.scalars().all()),
            threads=list(thread_res.scalars().all()),
            booklists=list(booklist_res.scalars().all()),
        )
