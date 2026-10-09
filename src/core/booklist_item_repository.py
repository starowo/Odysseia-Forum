import logging
from collections.abc import AsyncIterator
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import Float, case, cast
from sqlmodel import and_, asc, desc, func, select

from api.v1.schemas.booklist import BooklistItemUpdateRequest
from api.v1.schemas.booklist.booklist_item_detail import BooklistItemDetail
from api.v1.schemas.search.author_detail import AuthorDetail
from core.booklist_sort_constants import (
    DEFAULT_SORT_METHOD,
    DEFAULT_SORT_ORDER,
    SORT_METHOD_COLUMN_MAP,
)
from dto.open_graph import OpenGraphWorkCandidateDTO
from models import Author, Booklist, BooklistItem, Thread
from shared.enum.search_config_type import SearchConfigDefaults

logger = logging.getLogger(__name__)


def _apply_item_sorting(
    query,
    sort_method: str,
    sort_order: str,
    time_decay: float = SearchConfigDefaults.REDDIT_HOT_TIME_DECAY.value,
):
    """根据排序方式与顺序对书单帖子查询应用 ORDER BY。"""
    if sort_method == "hot":
        # Reddit Hot: log10(max(1, reaction_count)) + (epoch(created_at) / time_decay)
        ln10 = 2.302585092994046
        reaction_score = (
            func.log(
                case(
                    (Thread.reaction_count > 1, cast(Thread.reaction_count, Float)),
                    else_=1.0,
                )
            )
            / ln10
        )
        time_score = func.extract("epoch", Thread.created_at).cast(Float) / float(
            time_decay
        )
        return query.order_by((reaction_score + time_score).desc())

    order_func = asc if sort_order == "asc" else desc
    sort_field = SORT_METHOD_COLUMN_MAP.get(sort_method, BooklistItem.created_at)
    return query.order_by(order_func(sort_field))


class BooklistItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_open_graph_visible_items(
        self, booklist_id: int, excluded_channel_ids: set[int]
    ) -> int:
        """实时统计书单中当前公开且非深渊的作品数量。"""
        statement = (
            select(func.count(Thread.id))
            .join(BooklistItem, BooklistItem.thread_id == Thread.thread_id)  # type: ignore[arg-type]
            .where(
                BooklistItem.booklist_id == booklist_id,
                Thread.show_flag.is_(True),  # type: ignore[attr-defined]
                Thread.not_found_count == 0,
            )
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        result = await self.session.execute(statement)
        return int(result.scalar_one() or 0)

    async def stream_open_graph_works(
        self, booklist_id: int, excluded_channel_ids: set[int]
    ) -> AsyncIterator[OpenGraphWorkCandidateDTO]:
        """按热度与稳定次序流式返回书单代表作品候选。"""
        statement = (
            select(
                Thread.thread_id,
                Thread.title,
                Thread.thumbnail_urls,
                Thread.reaction_count,
                Thread.created_at,
            )
            .join(BooklistItem, BooklistItem.thread_id == Thread.thread_id)  # type: ignore[arg-type]
            .where(
                BooklistItem.booklist_id == booklist_id,
                Thread.show_flag.is_(True),  # type: ignore[attr-defined]
                Thread.not_found_count == 0,
            )
            .order_by(
                Thread.reaction_count.desc(),
                Thread.created_at.desc(),
                Thread.id.asc(),
            )
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        result = await self.session.stream(statement)
        async for row in result:
            yield OpenGraphWorkCandidateDTO(
                thread_id=int(row.thread_id),
                title=row.title,
                thumbnail_urls=list(row.thumbnail_urls or []),
                reaction_count=int(row.reaction_count or 0),
                created_at=row.created_at,
            )

    async def are_open_graph_sources_valid(
        self,
        booklist_id: int,
        thread_ids: list[int],
        excluded_channel_ids: set[int],
    ) -> bool:
        """批量确认缓存来源仍可见、非深渊且仍属于指定书单。"""
        unique_thread_ids = set(thread_ids)
        if not unique_thread_ids:
            return True
        statement = (
            select(func.count(Thread.id))
            .join(BooklistItem, BooklistItem.thread_id == Thread.thread_id)  # type: ignore[arg-type]
            .where(
                BooklistItem.booklist_id == booklist_id,
                Thread.thread_id.in_(unique_thread_ids),  # type: ignore[attr-defined]
                Thread.show_flag.is_(True),  # type: ignore[attr-defined]
                Thread.not_found_count == 0,
            )
        )
        if excluded_channel_ids:
            statement = statement.where(
                Thread.channel_id.not_in(excluded_channel_ids)  # type: ignore[attr-defined]
            )
        count = (await self.session.execute(statement)).scalar_one()
        return int(count) == len(unique_thread_ids)

    async def update_booklist_item(
        self, booklist_id: int, thread_id: int, update_data: BooklistItemUpdateRequest
    ) -> Optional[BooklistItem]:
        """
        更新书单项信息（推荐语、排序权重）
        """
        statement = select(BooklistItem).where(
            and_(
                BooklistItem.booklist_id == booklist_id,
                BooklistItem.thread_id == thread_id,
            )
        )
        result = await self.session.execute(statement)
        item = result.scalar_one_or_none()

        if not item:
            return None

        update_fields = update_data.model_dump(exclude_unset=True)
        if not update_fields:
            return item  # 没有需要更新的字段

        for key, value in update_fields.items():
            setattr(item, key, value)

        self.session.add(item)
        try:
            await self.session.commit()
            await self.session.refresh(item)
            # logger.info(f"书单项 (书单ID: {booklist_id}, 帖子ID: {thread_id}) 已更新")
            return item
        except Exception as e:
            logger.error(f"更新书单项失败: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_booklist_item_detail(
        self, booklist_id: int, thread_id: int
    ) -> Optional[BooklistItemDetail]:
        """
        获取单个书单项的详细信息
        """
        query = (
            select(BooklistItem, Thread, Author)
            .join(Thread, BooklistItem.thread_id == Thread.thread_id)  # type: ignore
            .join(Author, Thread.author_id == Author.id)  # type: ignore
            .where(
                and_(
                    BooklistItem.booklist_id == booklist_id,
                    BooklistItem.thread_id == thread_id,
                )
            )
            .options(selectinload(Thread.tags))  # type: ignore
        )
        result = await self.session.execute(query)
        row = result.one_or_none()

        if not row:
            return None

        item, thread, author = row
        author_detail = AuthorDetail.model_validate(author)
        item_detail = BooklistItemDetail(
            booklist_item_id=item.id,
            thread_id=thread.thread_id,
            guild_id=thread.guild_id,
            channel_id=thread.channel_id,
            title=thread.title,
            author=author_detail,
            created_at=thread.created_at,
            last_active_at=thread.last_active_at,
            reaction_count=thread.reaction_count,
            reply_count=thread.reply_count,
            display_count=thread.display_count,
            first_message_excerpt=thread.first_message_excerpt,
            latest_update_at=thread.latest_update_at,
            latest_update_link=thread.latest_update_link,
            collection_count=thread.collection_count,
            thumbnail_urls=thread.thumbnail_urls or [],
            tags=[tag.name for tag in thread.tags],
            virtual_tags=[],
            comment=item.comment,
            display_order=item.display_order,
            added_at=item.created_at,
            tournament_participated_at=item.tournament_participated_at,
            collected_flag=False,
        )
        return item_detail

    async def get_fallback_covers(self, booklist_ids: List[int]) -> Dict[int, str]:
        """
        为无封面书单批量取“最近加入的 item”所属 Thread 的第一张 thumbnail。

        统一按 BooklistItem.display_order DESC 取首条（等价加入时间倒序），不按 display_type 分支。
        当首条 item 的 thumbnail_urls 为空时，按排序顺序回退到下一条候选，
        直至找到带非空 thumbnail_urls 的 item 或候选耗尽。
        返回 {booklist_id: thumbnail_url}，找不到候选的书单不出现。
        """
        if not booklist_ids:
            return {}

        # 取每个书单前 N 条候选，首条无缩略图时可在 Python 端顺序回退
        FALLBACK_CANDIDATE_LIMIT = 10

        rn = (
            func.row_number()
            .over(
                partition_by=BooklistItem.booklist_id,
                order_by=(desc(BooklistItem.display_order), desc(BooklistItem.id)),
            )
            .label("rn")
        )

        ranked_subq = (
            select(
                BooklistItem.booklist_id.label("booklist_id"),
                Thread.thumbnail_urls.label("thumbnail_urls"),
                rn,
            )
            .join(Thread, BooklistItem.thread_id == Thread.thread_id)  # type: ignore
            .where(BooklistItem.booklist_id.in_(booklist_ids))  # type: ignore
            .subquery()
        )

        stmt = (
            select(
                ranked_subq.c.booklist_id,
                ranked_subq.c.thumbnail_urls,
                ranked_subq.c.rn,
            )
            .where(ranked_subq.c.rn <= FALLBACK_CANDIDATE_LIMIT)
            .order_by(ranked_subq.c.booklist_id, ranked_subq.c.rn)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        covers: Dict[int, str] = {}
        for booklist_id, thumbnail_urls, _ in rows:
            bid = int(booklist_id)
            if bid in covers:
                # 已经选定更靠前的候选，后续行跳过
                continue
            if not thumbnail_urls:
                continue
            if isinstance(thumbnail_urls, list) and thumbnail_urls:
                covers[bid] = thumbnail_urls[0]
        return covers

    async def get_booklist_items_with_details(
        self,
        booklist_id: int,
        default_sort_method: str = DEFAULT_SORT_METHOD,
        default_sort_order: str = DEFAULT_SORT_ORDER,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BooklistItemDetail], int]:
        """
        分页获取书单内的帖子详情，并根据书单的默认排序方式排序
        """

        base_query = (
            select(BooklistItem, Thread, Author)
            .join(Thread, BooklistItem.thread_id == Thread.thread_id)  # type: ignore
            .join(Author, Thread.author_id == Author.id)  # type: ignore
            .where(BooklistItem.booklist_id == booklist_id)  # type: ignore
            .options(selectinload(Thread.tags))  # type: ignore
        )

        # 计数（不包含排序）
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one_or_none() or 0

        # 应用排序
        sorted_query = _apply_item_sorting(
            base_query, default_sort_method, default_sort_order
        )

        # 获取数据
        data_stmt = sorted_query.offset(offset).limit(limit)
        result = await self.session.execute(data_stmt)
        rows = result.all()

        items = []
        for item, thread, author in rows:
            author_detail = AuthorDetail.model_validate(author)
            item_detail = BooklistItemDetail(
                booklist_item_id=item.id,
                thread_id=thread.thread_id,
                guild_id=thread.guild_id,
                channel_id=thread.channel_id,
                title=thread.title,
                author=author_detail,
                created_at=thread.created_at,
                last_active_at=thread.last_active_at,
                reaction_count=thread.reaction_count,
                reply_count=thread.reply_count,
                display_count=thread.display_count,
                first_message_excerpt=thread.first_message_excerpt,
                latest_update_at=thread.latest_update_at,
                latest_update_link=thread.latest_update_link,
                collection_count=thread.collection_count,
                thumbnail_urls=thread.thumbnail_urls or [],
                tags=[tag.name for tag in thread.tags],
                virtual_tags=[],
                comment=item.comment,
                display_order=item.display_order,
                added_at=item.created_at,
                tournament_participated_at=item.tournament_participated_at,
                collected_flag=False,
            )
            items.append(item_detail)

        return items, total

    async def get_tournament_info_by_thread_ids(
        self, thread_ids: list[int]
    ) -> dict[int, list[dict]]:
        """
        批量查询 thread_id → 所属赛事书单信息映射。

        只查询 is_tournament=True 的书单，返回 {thread_id: [{booklist_id, booklist_name}, ...]}。
        """
        if not thread_ids:
            return {}

        stmt = (
            select(BooklistItem.thread_id, Booklist.id, Booklist.title)
            .join(Booklist, Booklist.id == BooklistItem.booklist_id)  # type: ignore[arg-type]
            .where(
                Booklist.is_tournament.is_(True),  # type: ignore[arg-type]
                BooklistItem.thread_id.in_(thread_ids),  # type: ignore[arg-type]
            )
        )
        rows = (await self.session.execute(stmt)).all()
        result: dict[int, list[dict]] = {}
        for tid, bl_id, bl_title in rows:
            result.setdefault(tid, []).append(
                {"booklist_id": bl_id, "booklist_name": bl_title}
            )
        return result
