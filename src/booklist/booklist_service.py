import logging
from typing import List, Optional, Tuple
from sqlalchemy import false
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete, and_, func, desc, asc, or_

from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData
from api.v1.schemas.search.author import AuthorDetail
from shared.enum.collection_type import CollectionType
from shared.models.booklist import Booklist
from shared.models.booklist_item import BooklistItem
from shared.models.user_collection import UserCollection
from shared.models.thread import Thread
from shared.models.author import Author
from src.api.v1.schemas.booklist import BooklistItemDetail

logger = logging.getLogger(__name__)


class BooklistService:
    """书单服务，提供书单的CRUD操作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_booklist(
        self,
        owner_id: int,
        title: str,
        description: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        is_public: bool = True,
        display_type: int = 1,
    ) -> Booklist:
        """
        创建新书单
        """
        booklist = Booklist(
            owner_id=owner_id,
            title=title,
            description=description,
            cover_image_url=cover_image_url,
            is_public=is_public,
            display_type=display_type,
            item_count=0,
            collection_count=0,
            view_count=0,
        )
        self.session.add(booklist)
        try:
            await self.session.commit()
            await self.session.refresh(booklist)
            logger.info(f"用户 {owner_id} 创建书单 {booklist.id}: {title}")
            return booklist
        except Exception as e:
            logger.error(f"创建书单失败: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_booklist(self, booklist_id: int) -> Optional[Booklist]:
        """
        根据ID获取书单
        """
        statement = select(Booklist).where(Booklist.id == booklist_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_booklist(
        self,
        booklist_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        is_public: Optional[bool] = None,
        display_type: Optional[int] = None,
    ) -> Optional[Booklist]:
        """
        更新书单信息
        """
        booklist = await self.get_booklist(booklist_id)
        if not booklist:
            return None

        if title is not None:
            booklist.title = title
        if description is not None:
            booklist.description = description
        if cover_image_url is not None:
            booklist.cover_image_url = cover_image_url
        if is_public is not None:
            booklist.is_public = is_public
        if display_type is not None:
            booklist.display_type = display_type

        self.session.add(booklist)
        try:
            await self.session.commit()
            await self.session.refresh(booklist)
            logger.info(f"书单 {booklist_id} 已更新")
            return booklist
        except Exception as e:
            logger.error(f"更新书单失败: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def delete_booklist(self, booklist_id: int) -> bool:
        """
        删除书单及其所有关联项
        """
        # 先删除所有关联项
        statement_items = delete(BooklistItem).where(
            BooklistItem.booklist_id == booklist_id  # type: ignore
        )
        await self.session.execute(statement_items)
        # 删除书单
        statement = delete(Booklist).where(Booklist.id == booklist_id)  # type: ignore
        result = await self.session.execute(statement)
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"书单 {booklist_id} 已删除")
        return deleted

    async def list_booklists(
        self,
        owner_id: Optional[int] = None,
        is_public: Optional[bool] = None,
        keywords: Optional[str] = None,
        collected_by_user_id: Optional[int] = None,
        sort_method: int = 4,
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Booklist], int]:
        """
        分页搜索书单
        """
        offset = (page - 1) * per_page
        query = select(Booklist)

        if owner_id is not None:
            query = query.where(Booklist.owner_id == owner_id)
        if is_public is not None:
            query = query.where(Booklist.is_public == is_public)
        if keywords:
            search_pattern = f"%{keywords}%"
            query = query.where(
                or_(
                    getattr(Booklist.title, "ilike")(search_pattern),
                    getattr(Booklist.description, "ilike")(search_pattern),
                )
            )
        if collected_by_user_id is not None:
            query = query.join(
                UserCollection,
                and_(
                    Booklist.id == UserCollection.target_id,
                    UserCollection.user_id == collected_by_user_id,
                    UserCollection.target_type == CollectionType.BOOKLIST.value,
                ),
            )

        # 排序
        sort_field = {
            1: Booklist.item_count,
            2: Booklist.view_count,
            3: Booklist.collection_count,
            4: Booklist.created_at,
            5: Booklist.updated_at,
        }.get(sort_method, Booklist.created_at)

        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_field))
        else:
            query = query.order_by(desc(sort_field))

        # 计数
        count_stmt = select(func.count()).select_from(query.alias("sub"))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one_or_none() or 0

        # 获取数据
        data_stmt = query.offset(offset).limit(per_page)
        result = await self.session.execute(data_stmt)
        booklists = result.scalars().all()

        return list(booklists), total

    async def add_threads_to_booklist(
        self,
        booklist_id: int,
        items: List[BooklistItemAddData],
    ) -> List[BooklistItem]:
        """
        向书单批量添加帖子
        """
        thread_ids = [item.thread_id for item in items]
        if not thread_ids:
            return []

        # 检查已存在的帖子
        existing_stmt = select(BooklistItem.thread_id).where(
            BooklistItem.booklist_id == booklist_id,
            BooklistItem.thread_id.in_(thread_ids),  # type: ignore
        )
        result = await self.session.execute(existing_stmt)
        existing_thread_ids = set(result.scalars().all())

        # 确定需要添加的新帖子
        new_items_to_add = [
            item for item in items if item.thread_id not in existing_thread_ids
        ]

        if not new_items_to_add:
            return []

        # 获取当前最大的 display_order 以便追加
        max_order_result = await self.session.execute(
            select(func.max(BooklistItem.display_order)).where(
                BooklistItem.booklist_id == booklist_id
            )  # type: ignore
        )
        max_order = max_order_result.scalar_one_or_none() or 0

        # 创建新的 BooklistItem 对象
        new_booklist_items = []
        for i, item_data in enumerate(new_items_to_add):
            display_order = item_data.display_order
            if display_order is None:
                display_order = max_order + 1 + i

            new_booklist_items.append(
                BooklistItem(
                    booklist_id=booklist_id,
                    thread_id=item_data.thread_id,
                    comment=item_data.comment,
                    display_order=display_order,
                )
            )

        self.session.add_all(new_booklist_items)

        # 更新书单的 item_count
        booklist = await self.get_booklist(booklist_id)
        if booklist:
            booklist.item_count += len(new_booklist_items)
            self.session.add(booklist)

        try:
            await self.session.commit()
            for item in new_booklist_items:
                await self.session.refresh(item)
            # logger.info(f"{len(new_booklist_items)} 个帖子已添加到书单 {booklist_id}")
            return new_booklist_items
        except Exception as e:
            logger.error(f"批量添加帖子到书单失败: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def remove_threads_from_booklist(
        self, booklist_id: int, thread_ids: List[int]
    ) -> int:
        """
        从书单批量移除帖子
        """
        if not thread_ids:
            return 0

        statement = delete(BooklistItem).where(
            and_(
                BooklistItem.booklist_id == booklist_id,  # type: ignore
                BooklistItem.thread_id.in_(thread_ids),  # type: ignore
            )
        )
        result = await self.session.execute(statement)
        deleted_count = result.rowcount

        if deleted_count > 0:
            # 更新书单的item_count
            booklist = await self.get_booklist(booklist_id)
            if booklist:
                booklist.item_count -= deleted_count
                if booklist.item_count < 0:
                    booklist.item_count = 0
                self.session.add(booklist)
                await self.session.commit()
            logger.info(f"{deleted_count} 个帖子已从书单 {booklist_id} 移除")

        return deleted_count

    async def increment_view_count(self, booklist_id: int) -> None:
        """
        增加书单的查看次数
        """
        booklist = await self.get_booklist(booklist_id)
        if booklist:
            booklist.view_count += 1
            self.session.add(booklist)
            await self.session.commit()

    async def update_collection_count(self, booklist_id: int, delta: int) -> None:
        """
        更新书单的被收藏次数（delta 为 +1 或 -1）
        """
        booklist = await self.get_booklist(booklist_id)
        if booklist:
            booklist.collection_count += delta
            if booklist.collection_count < 0:
                booklist.collection_count = 0
            self.session.add(booklist)
            await self.session.commit()
