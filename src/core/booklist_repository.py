from core.tag_binding_repository import TagBindingRepository
import logging
from typing import List, Optional, Set, Tuple

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, asc, delete, desc, func, select

from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData
from core.booklist_sort_constants import DEFAULT_SORT_METHOD, DEFAULT_SORT_ORDER
from core.tag_query import tag_filters, tag_name_filters, require_current_tag_ids
from dto.search.fts_result_dto import FTSResultDTO
from dto.open_graph import BooklistShareQueryDTO
from models import Booklist, BooklistItem, BooklistPublish, UserCollection
from shared.enum import CollectionType
from shared.fts_utils import build_fts_conditions
from shared.time_utils import utc_now

logger = logging.getLogger(__name__)


class BooklistRepository:
    """书单仓库，提供书单的CRUD操作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_default_booklist(self, owner_id: int) -> Booklist:
        """获取用户的默认书单，如果不存在则自动创建"""
        statement = select(Booklist).where(
            and_(Booklist.owner_id == owner_id, Booklist.is_default)
        )
        result = await self.session.execute(statement)
        booklist = result.scalar_one_or_none()

        if not booklist:
            booklist = Booklist(
                owner_id=owner_id,
                title="默认收藏",
                description="默认收藏夹",
                is_public=False,  # 默认书单设定为私有
                is_anonymous=False,
                is_default=True,
                default_sort_method=DEFAULT_SORT_METHOD.value,
                default_sort_order=DEFAULT_SORT_ORDER.value,
                item_count=0,
                collection_count=0,
                view_count=0,
            )
            self.session.add(booklist)
            await self.session.commit()
            await self.session.refresh(booklist)
            logger.debug(f"为用户 {owner_id} 创建了默认书单 {booklist.id}")

        return booklist

    async def create_booklist(
        self,
        owner_id: int,
        title: str,
        description: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        is_public: bool = True,
        is_anonymous: bool = False,
        default_sort_method: str = DEFAULT_SORT_METHOD.value,
        default_sort_order: str = DEFAULT_SORT_ORDER.value,
        is_tournament: bool = False,
        tournament_channel_id: Optional[int] = None,
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
            is_anonymous=is_anonymous,
            default_sort_method=default_sort_method,
            default_sort_order=default_sort_order,
            is_tournament=is_tournament,
            tournament_channel_id=tournament_channel_id,
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

    async def get_open_graph_booklist(
        self, booklist_id: int
    ) -> BooklistShareQueryDTO | None:
        """查询公开书单分享所需标量并在 Session 内转换为 DTO。"""
        statement = select(
            Booklist.owner_id,
            Booklist.title,
            Booklist.description,
            Booklist.cover_image_url,
            Booklist.is_anonymous,
            Booklist.is_tournament,
            Booklist.collection_count,
            Booklist.view_count,
            Booklist.created_at,
            Booklist.updated_at,
        ).where(Booklist.id == booklist_id, Booklist.is_public.is_(True))  # type: ignore[attr-defined]
        row = (await self.session.execute(statement)).first()
        if row is None:
            return None
        return BooklistShareQueryDTO(
            owner_id=int(row.owner_id),
            title=row.title,
            description=row.description,
            cover_image_url=row.cover_image_url,
            is_anonymous=bool(row.is_anonymous),
            is_tournament=bool(row.is_tournament),
            collection_count=int(row.collection_count or 0),
            view_count=int(row.view_count or 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_booklist_by_tournament_channel_id(
        self, tournament_channel_id: int
    ) -> Optional[Booklist]:
        """根据赛事频道ID查找赛事书单"""
        statement = select(Booklist).where(
            Booklist.tournament_channel_id == tournament_channel_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def set_publish_status(
        self, booklist_id: int, publish_status: int, *, commit: bool = True
    ) -> bool:
        """更新书单发布状态。"""
        statement = (
            update(Booklist)
            .where(Booklist.id == booklist_id)  # type: ignore
            .values(publish_status=publish_status)
        )
        result = await self.session.execute(statement)
        if commit:
            await self.session.commit()
        return result.rowcount > 0

    async def update_booklist(
        self,
        booklist_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        is_public: Optional[bool] = None,
        is_anonymous: Optional[bool] = None,
        default_sort_method: Optional[str] = None,
        default_sort_order: Optional[str] = None,
        display_thread_id: Optional[int] = None,
        display_channel_id: Optional[int] = None,
        display_guild_id: Optional[int] = None,
    ) -> Optional[Booklist]:
        """
        更新书单信息
        """
        update_values = {
            "title": title,
            "description": description,
            "cover_image_url": cover_image_url,
            "is_public": is_public,
            "is_anonymous": is_anonymous,
            "default_sort_method": default_sort_method,
            "default_sort_order": default_sort_order,
            "display_thread_id": display_thread_id,
            "display_channel_id": display_channel_id,
            "display_guild_id": display_guild_id,
        }

        # 移除未提供值的键
        update_data = {k: v for k, v in update_values.items() if v is not None}

        if not update_data:
            return await self.get_booklist(booklist_id)

        try:
            # 锁定并刷新最新原文，ORM 编辑触发统一的搜索向量维护事件。
            statement = (
                select(Booklist)
                .where(Booklist.id == booklist_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            booklist = (await self.session.execute(statement)).scalar_one_or_none()
            if booklist is None:
                await self.session.rollback()
                return None
            for field, value in update_data.items():
                setattr(booklist, field, value)
            # 保留原编辑入口每次有效调用均更新业务时间的行为。
            booklist.updated_at = utc_now()
            self.session.add(booklist)

            await self.session.commit()
            # logger.info(f"书单 {booklist_id} 已更新")
            return await self.get_booklist(booklist_id)

        except Exception as e:
            logger.error(f"更新书单失败: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def delete_booklist(self, booklist_id: int) -> bool:
        """
        删除书单及其所有关联项
        """
        # 删除所有关联项
        statement_items = delete(BooklistItem).where(
            BooklistItem.booklist_id == booklist_id  # type: ignore
        )
        await self.session.execute(statement_items)
        # 删除所有发布记录
        statement_publish = delete(BooklistPublish).where(
            BooklistPublish.booklist_id == booklist_id  # type: ignore
        )
        await self.session.execute(statement_publish)
        # 删除书单
        await TagBindingRepository(self.session).delete_targets(
            "booklist", [booklist_id]
        )
        statement = delete(Booklist).where(Booklist.id == booklist_id)  # type: ignore
        result = await self.session.execute(statement)
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"书单 {booklist_id} 已删除")
        return deleted

    async def get_fts_matched_booklist_ids(
        self,
        keywords: str | None,
        exclude_keywords: str | None,
        redis_client=None,
    ) -> FTSResultDTO:
        """FTS 书单搜索，返回可直接嵌入 WHERE 的 filter 条件。

        委托给共享模块 ``shared.fts_utils.build_fts_conditions``。
        """
        return await build_fts_conditions(
            Booklist.search_vector,
            keywords,
            exclude_keywords,
            exemption_markers=None,
            redis_client=redis_client,
        )

    async def list_booklists(
        self,
        owner_id: Optional[int] = None,
        is_public: Optional[bool] = None,
        is_tournament: Optional[bool] = None,
        keywords: Optional[str] = None,
        exclude_keywords: Optional[str] = None,
        owner_ids: Optional[list[int]] = None,
        included_thread_id: Optional[int] = None,
        collected_by_user_id: Optional[int] = None,
        tournament_channel_id: Optional[int] = None,
        sort_method: int = 4,
        sort_order: str = "desc",
        limit: int = 10,
        offset: int = 0,
        include_tag_ids: list[int] | None = None,
        exclude_tag_ids: list[int] | None = None,
        tag_logic: str = "and",
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
    ) -> Tuple[List[Booklist], int]:
        """
        分页搜索书单（支持 FTS 全文搜索）
        """
        await require_current_tag_ids(
            self.session, [*(include_tag_ids or []), *(exclude_tag_ids or [])]
        )
        query = select(Booklist)
        query = query.where(
            *tag_filters(
                "booklist",
                Booklist.id,
                include_tag_ids,
                exclude_tag_ids,
                tag_logic,
            )
        )

        query = query.where(
            *await tag_name_filters(
                self.session,
                "booklist",
                Booklist.id,
                include_tags,
                exclude_tags,
                tag_logic,
            )
        )

        if owner_id is not None:
            query = query.where(Booklist.owner_id == owner_id)
        if owner_ids is not None:
            query = query.where(Booklist.owner_id.in_(owner_ids))  # type: ignore
        if is_public is not None:
            query = query.where(Booklist.is_public == is_public)
        if is_tournament is not None:
            query = query.where(Booklist.is_tournament == is_tournament)
        if tournament_channel_id is not None:
            query = query.where(Booklist.tournament_channel_id == tournament_channel_id)
        if keywords or exclude_keywords:
            fts_result = await self.get_fts_matched_booklist_ids(
                keywords=keywords,
                exclude_keywords=exclude_keywords,
            )
            if fts_result.has_include:
                for cond in fts_result.include_conditions:
                    query = query.where(cond)
            if fts_result.has_exclude:
                query = query.where(~fts_result.exclude_condition)
        if collected_by_user_id is not None:
            query = query.join(
                UserCollection,
                and_(
                    Booklist.id == UserCollection.target_id,
                    UserCollection.user_id == collected_by_user_id,
                    UserCollection.target_type == CollectionType.BOOKLIST.value,
                ),
            )
        if included_thread_id is not None:
            query = query.join(
                BooklistItem,
                Booklist.id == BooklistItem.booklist_id,  # type: ignore
            ).where(BooklistItem.thread_id == included_thread_id)

        # 排序
        sort_field_map = {
            1: Booklist.item_count,
            2: Booklist.view_count,
            3: Booklist.collection_count,
            4: Booklist.created_at,
            5: Booklist.updated_at,
            6: UserCollection.created_at,
        }
        sort_field = sort_field_map.get(sort_method, Booklist.created_at)

        # 如果按收藏时间排序，但 collected_by_user_id 未提供，则回退到默认排序
        if sort_method == 6 and collected_by_user_id is None:
            sort_field = Booklist.created_at

        order_func = asc if sort_order.lower() == "asc" else desc
        query = query.order_by(order_func(sort_field))

        # 计数
        count_stmt = select(func.count()).select_from(query.alias("sub"))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one_or_none() or 0

        # 获取数据
        data_stmt = query.offset(offset).limit(limit)
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

        # 获取书单所有者ID，以便写入 BooklistItem
        booklist = await self.get_booklist(booklist_id)
        owner_id = booklist.owner_id if booklist else 0

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
                    thread_id=item_data.thread_id,  # type: ignore
                    owner_id=owner_id,
                    comment=item_data.comment,
                    display_order=display_order,
                    tournament_participated_at=getattr(
                        item_data, "tournament_participated_at", None
                    ),
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
            # logger.info(f"{deleted_count} 个帖子已从书单 {booklist_id} 移除")

        return deleted_count

    async def add_thread_to_booklists(
        self,
        thread_id: int,
        booklist_ids: List[int],
        owner_id: int,
        comment: Optional[str] = None,
    ) -> List[int]:
        """
        将一个帖子批量添加到多个书单。

        跳过已存在的项（on_conflict_do_nothing 保证幂等），
        返回实际新增了帖子的书单 ID 列表。
        """
        if not booklist_ids:
            return []

        # 获取各书单当前 max(display_order)
        max_stmt = (
            select(
                BooklistItem.booklist_id,
                func.max(BooklistItem.display_order).label("max_order"),
            )
            .where(BooklistItem.booklist_id.in_(booklist_ids))  # type: ignore
            .group_by(BooklistItem.booklist_id)  # type: ignore
        )
        max_result = await self.session.execute(max_stmt)
        max_orders: dict = {row[0]: row[1] or 0 for row in max_result.fetchall()}

        # 构建插入值
        values = [
            {
                "booklist_id": bid,
                "thread_id": thread_id,
                "owner_id": owner_id,
                "display_order": max_orders.get(bid, 0) + 1,
                "comment": comment,
            }
            for bid in booklist_ids
        ]

        # 批量插入，冲突时跳过，并返回实际插入的书单 ID
        stmt = (
            insert(BooklistItem)
            .values(values)
            .on_conflict_do_nothing()
            .returning(BooklistItem.booklist_id)  # type: ignore
        )
        result = await self.session.execute(stmt)
        inserted_ids: List[int] = [row[0] for row in result.fetchall()]

        # 更新 item_count：仅对实际新增了帖子的书单 +1
        if inserted_ids:
            update_stmt = (
                update(Booklist)
                .where(Booklist.id.in_(inserted_ids))  # type: ignore
                .values(item_count=Booklist.item_count + 1)
            )
            await self.session.execute(update_stmt)

        await self.session.commit()
        return inserted_ids

    async def remove_thread_from_booklists(
        self, thread_id: int, booklist_ids: List[int]
    ) -> List[int]:
        """
        将一个帖子从多个书单中批量移除。

        返回实际移除了帖子的书单 ID 列表。
        """
        if not booklist_ids:
            return []

        # 批量删除并返回被删除的行所属的书单 ID
        from collections import Counter

        stmt = (
            delete(BooklistItem)
            .where(
                and_(
                    BooklistItem.thread_id == thread_id,  # type: ignore
                    BooklistItem.booklist_id.in_(booklist_ids),  # type: ignore
                )
            )
            .returning(BooklistItem.booklist_id)  # type: ignore
        )
        result = await self.session.execute(stmt)
        removed_ids: List[int] = [row[0] for row in result.fetchall()]

        # 更新 item_count：按书单分组递减
        if removed_ids:
            counts = Counter(removed_ids)
            for bid, cnt in counts.items():
                booklist = await self.get_booklist(bid)
                if booklist:
                    booklist.item_count -= cnt
                    if booklist.item_count < 0:
                        booklist.item_count = 0
                    self.session.add(booklist)

        await self.session.commit()
        return list(set(removed_ids))

    async def update_thread_comment_in_booklists(
        self, thread_id: int, booklist_ids: List[int], comment: str
    ) -> None:
        """批量更新一个帖子在多个书单中的推荐语。"""
        if not booklist_ids:
            return

        statement = (
            update(BooklistItem)
            .where(
                and_(
                    BooklistItem.thread_id == thread_id,  # type: ignore
                    BooklistItem.booklist_id.in_(booklist_ids),  # type: ignore
                )
            )
            .values(comment=comment)
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def get_threads_in_users_booklists(
        self, owner_id: int, thread_ids: List[int]
    ) -> Set[int]:
        """
        查询指定的一批帖子中，有哪些已经被该用户加入过任何书单。
        """
        if not thread_ids:
            return set()

        statement = select(BooklistItem.thread_id).where(
            and_(
                BooklistItem.owner_id == owner_id,
                BooklistItem.thread_id.in_(thread_ids),  # type: ignore
            )
        )
        result = await self.session.execute(statement)
        return set(result.scalars().all())

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

    async def update_collection_counts(
        self, booklist_ids: List[int], delta: int
    ) -> None:
        """
        批量更新书单的被收藏次数
        """
        if not booklist_ids:
            return

        try:
            statement = (
                update(Booklist)
                .where(Booklist.id.in_(booklist_ids))  # type: ignore
                .values(collection_count=Booklist.collection_count + delta)
            )
            await self.session.execute(statement)
            await self.session.commit()
        except Exception as e:
            logger.error(f"批量更新书单收藏数失败: {e}", exc_info=True)
            await self.session.rollback()
            raise
