import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, asc, desc, func, select

from api.v1.schemas.booklist import BooklistItemUpdateRequest
from api.v1.schemas.booklist.booklist_item_detail import BooklistItemDetail
from api.v1.schemas.search.author import AuthorDetail
from models import Author, BooklistItem, Thread

logger = logging.getLogger(__name__)


class BooklistItemService:
    def __init__(self, session: AsyncSession):
        self.session = session

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
            logger.info(f"书单项 (书单ID: {booklist_id}, 帖子ID: {thread_id}) 已更新")
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
            channel_id=thread.channel_id,
            title=thread.title,
            author=author_detail,
            created_at=thread.created_at,
            reaction_count=thread.reaction_count,
            reply_count=thread.reply_count,
            thumbnail_urls=thread.thumbnail_urls or [],
            comment=item.comment,
            display_order=item.display_order,
            added_at=item.created_at,
            collected_flag=False,
        )
        return item_detail

    async def get_booklist_items_with_details(
        self,
        booklist_id: int,
        display_type: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[BooklistItemDetail], int]:
        """
        分页获取书单内的帖子详情，并根据指定的排序方式排序
        """

        query = (
            select(BooklistItem, Thread, Author)
            .join(Thread, BooklistItem.thread_id == Thread.thread_id)  # type: ignore
            .join(Author, Thread.author_id == Author.id)  # type: ignore
            .where(BooklistItem.booklist_id == booklist_id)  # type: ignore
        )

        # 根据 display_type 应用不同的排序规则
        if display_type == 2:
            # 按 display_order 升序
            query = query.order_by(asc(BooklistItem.display_order))
        else:
            # 默认按加入时间倒序
            query = query.order_by(desc(BooklistItem.created_at))

        # 计数
        count_stmt = select(func.count()).select_from(query.alias("sub"))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one_or_none() or 0

        # 获取数据
        data_stmt = query.offset(offset * limit).limit(limit)
        result = await self.session.execute(data_stmt)
        rows = result.all()

        items = []
        for item, thread, author in rows:
            author_detail = AuthorDetail.model_validate(author)
            item_detail = BooklistItemDetail(
                booklist_item_id=item.id,
                thread_id=thread.thread_id,
                channel_id=thread.channel_id,
                title=thread.title,
                author=author_detail,
                created_at=thread.created_at,
                reaction_count=thread.reaction_count,
                reply_count=thread.reply_count,
                thumbnail_urls=thread.thumbnail_urls or [],
                comment=item.comment,
                display_order=item.display_order,
                added_at=item.created_at,
                collected_flag=False,
            )
            items.append(item_detail)

        return items, total
