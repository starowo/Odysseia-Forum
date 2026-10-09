import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Sequence, Tuple, Type, TypeVar

from sqlalchemy import case, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import and_, delete, desc, func, select

from dto.collection.batch_add_result import BatchAddResult
from dto.collection.batch_remove_result import BatchRemoveResult
from core.booklist_repository import BooklistRepository
from core.redis_trend_service import RedisTrendService
from models import Booklist, BooklistItem, Thread, ThreadFollow, UserCollection
from shared.enum import CollectionType, ConstantEnum

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CollectionRepository:
    """封装与用户收藏相关的数据库操作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _record_thread_collection_trends(self, thread_ids: Sequence[int]) -> None:
        """为近期帖子记录用户维度去重后的收藏趋势。"""
        if not thread_ids:
            return

        threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=ConstantEnum.STATISTICS_THRESHOLD_DAYS.value
        )
        statement = select(Thread.thread_id, Thread.channel_id).where(
            Thread.thread_id.in_(thread_ids),  # type: ignore
            Thread.created_at >= threshold,
        )
        valid_threads = (await self.session.execute(statement)).all()
        trend_service = RedisTrendService()
        for thread_id, channel_id in valid_threads:
            await trend_service.record_increment(
                "collection",
                int(thread_id),
                int(channel_id),
                count=1,
            )

    async def add_collection(
        self, user_id: int, target_type: int, target_id: int
    ) -> bool:
        """
        为用户添加一个收藏

        Returns:
            bool: 如果是新收藏则返回 True，如果已存在则返回 False
        """
        if target_type == CollectionType.THREAD.value:
            # 帖子类型，路由到默认书单
            repo = BooklistRepository(self.session)
            booklist = await repo.get_or_create_default_booklist(user_id)

            # 趋势和全局收藏数仅按“用户是否首次收藏该帖”计算一次。
            already_collected = await self.get_collected_target_ids(
                user_id, CollectionType.THREAD, [target_id]
            )
            is_net_new = target_id not in already_collected

            if booklist.id is None:
                raise ValueError("创建的书单没有ID")

            # 校验排重
            stmt = select(BooklistItem.id).where(
                and_(
                    BooklistItem.booklist_id == booklist.id,
                    BooklistItem.thread_id == target_id,
                )
            )
            if (await self.session.execute(stmt)).scalar_one_or_none():
                return False  # 已存在

            # 获取当前最大排序值
            max_order_result = await self.session.execute(
                select(func.max(BooklistItem.display_order)).where(
                    BooklistItem.booklist_id == booklist.id
                )
            )
            max_order = max_order_result.scalar_one_or_none() or 0

            new_item = BooklistItem(
                booklist_id=booklist.id,
                thread_id=target_id,
                owner_id=user_id,
                display_order=max_order + 1,
            )
            self.session.add(new_item)
            booklist.item_count += 1
            await self.session.commit()
            if is_net_new:
                await self._record_thread_collection_trends([target_id])
            return True
        else:
            # target_type == 2 (书单) , 操作 UserCollection
            new_collection = UserCollection(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
            )
            self.session.add(new_collection)
            try:
                await self.session.commit()
                return True
            except IntegrityError:
                logger.debug(
                    f"用户 {user_id} 尝试收藏已存在的目标 {target_type}:{target_id}"
                )
                await self.session.rollback()
                return False
            except Exception as e:
                logger.error(
                    f"为用户 {user_id} 添加收藏 {target_type}:{target_id} 时出错: {e}",
                    exc_info=True,
                )
                await self.session.rollback()
                raise

    async def remove_collection(
        self, user_id: int, target_type: int, target_id: int
    ) -> bool:
        """
        为用户移除一个收藏。

        Returns:
            bool: 如果成功移除了记录则返回 True，如果记录不存在则返回 False。
        """
        if target_type == CollectionType.THREAD.value:
            # 类型为帖子，路由到默认书单
            # 查找该帖子存在于用户的哪些书单中
            stmt = select(BooklistItem.booklist_id).where(
                BooklistItem.owner_id == user_id,
                BooklistItem.thread_id == target_id,
            )
            affected_booklists = (await self.session.execute(stmt)).scalars().all()

            if not affected_booklists:
                return False

            # 从用户的所有书单中删除该帖子
            del_stmt = delete(BooklistItem).where(
                BooklistItem.owner_id == user_id,  # type: ignore
                BooklistItem.thread_id == target_id,  # type: ignore
            )
            await self.session.execute(del_stmt)

            # 批量扣减受影响的书单 item_count
            update_stmt = (
                update(Booklist)
                .where(Booklist.id.in_(affected_booklists))  # type: ignore
                .values(item_count=func.greatest(0, Booklist.item_count - 1))
            )
            await self.session.execute(update_stmt)
            await self.session.commit()
            return True
        else:
            # target_type == 2 (书单) , 操作 UserCollection
            statement = delete(UserCollection).where(
                and_(
                    UserCollection.user_id == user_id,
                    UserCollection.target_type == target_type,
                    UserCollection.target_id == target_id,
                )
            )
            result = await self.session.execute(statement)
            await self.session.commit()
            return result.rowcount > 0

    async def add_collections(
        self, user_id: int, target_type: int, target_ids: List[int]
    ) -> BatchAddResult:
        """
        批量添加收藏（同一类型）。

        Args:
            user_id: 用户ID
            target_type: 目标类型
            target_ids: 目标ID列表

        Returns:
            包含成功添加的ID列表和计数的 DTO
        """
        if not target_ids:
            return BatchAddResult(added_ids=[], added_count=0, duplicate_count=0)

        if target_type == CollectionType.THREAD.value:
            # 帖子类型，路由到默认书单
            repo = BooklistRepository(self.session)
            booklist = await repo.get_or_create_default_booklist(user_id)

            # 先记录用户在任意书单中的已有收藏，防止跨书单重复计入趋势。
            already_collected = await self.get_collected_target_ids(
                user_id, CollectionType.THREAD, target_ids
            )

            # 确保书单有ID
            if booklist.id is None:
                raise ValueError("创建的书单没有ID")

            # 查询传入帖子是否在默认书单中已存在
            existing_stmt = select(BooklistItem.thread_id).where(
                BooklistItem.booklist_id == booklist.id,
                BooklistItem.thread_id.in_(target_ids),  # type: ignore
            )
            existing_ids = set(
                (await self.session.execute(existing_stmt)).scalars().all()
            )
            new_ids = [tid for tid in target_ids if tid not in existing_ids]
            net_new_ids = [tid for tid in new_ids if tid not in already_collected]

            if not new_ids:
                return BatchAddResult(
                    added_ids=[], added_count=0, duplicate_count=len(target_ids)
                )

            # 获取当前最大排序值
            max_order_result = await self.session.execute(
                select(func.max(BooklistItem.display_order)).where(
                    BooklistItem.booklist_id == booklist.id
                )
            )
            max_order = max_order_result.scalar_one_or_none() or 0

            # 批量插入新的书单项
            values = [
                {
                    "booklist_id": booklist.id,
                    "thread_id": tid,
                    "owner_id": user_id,
                    "display_order": max_order + 1 + i,
                }
                for i, tid in enumerate(new_ids)
            ]
            await self.session.execute(insert(BooklistItem).values(values))

            # 更新书单的帖子数量
            booklist.item_count += len(new_ids)
            await self.session.commit()

            # 仅为用户首次收藏的近期帖子记录趋势。
            await self._record_thread_collection_trends(net_new_ids)

            return BatchAddResult(
                added_ids=new_ids,
                added_count=len(new_ids),
                duplicate_count=len(target_ids) - len(new_ids),
            )
        else:
            # target_type == 2 (书单) , 操作 UserCollection
            # 找出哪些是新的收藏
            existing_stmt = select(UserCollection.target_id).where(
                UserCollection.user_id == user_id,
                UserCollection.target_type == target_type,
                UserCollection.target_id.in_(target_ids),  # type: ignore
            )
            result = await self.session.execute(existing_stmt)
            existing_ids = set(result.scalars().all())
            new_ids = [tid for tid in target_ids if tid not in existing_ids]

            if not new_ids:
                return BatchAddResult(
                    added_ids=[], added_count=0, duplicate_count=len(target_ids)
                )

            # 只插入新的收藏
            values = [
                {"user_id": user_id, "target_type": target_type, "target_id": tid}
                for tid in new_ids
            ]
            if values:
                stmt = insert(UserCollection).values(values).on_conflict_do_nothing()
                await self.session.execute(stmt)
                await self.session.commit()

            return BatchAddResult(
                added_ids=new_ids,
                added_count=len(new_ids),
                duplicate_count=len(target_ids) - len(new_ids),
            )

    async def remove_collections(
        self, user_id: int, target_type: int, target_ids: List[int]
    ) -> BatchRemoveResult:
        """
        批量移除收藏（同一类型）。

        Args:
            user_id: 用户ID
            target_type: 目标类型
            target_ids: 目标ID列表

        Returns:
            包含成功移除的ID列表和计数的 DTO
        """
        if not target_ids:
            return BatchRemoveResult(removed_ids=[], removed_count=0, not_found_count=0)

        if target_type == CollectionType.THREAD.value:
            # 帖子类型，路由到默认书单
            # 查询要删除的所有书单项 (书单ID，帖子ID)
            select_stmt = select(
                BooklistItem.booklist_id, BooklistItem.thread_id
            ).where(
                BooklistItem.owner_id == user_id,
                BooklistItem.thread_id.in_(target_ids),  # type: ignore
            )
            items_to_remove = (await self.session.execute(select_stmt)).all()

            if not items_to_remove:
                return BatchRemoveResult(
                    removed_ids=[], removed_count=0, not_found_count=len(target_ids)
                )

            # 统计各个书单分别被移除了几个帖子
            booklist_decrements = Counter(row.booklist_id for row in items_to_remove)
            # 去重提取所有被移除的帖子ID
            removed_thread_ids = list(set(row.thread_id for row in items_to_remove))

            # 删除书单项
            await self.session.execute(
                delete(BooklistItem).where(
                    BooklistItem.owner_id == user_id,  # type: ignore
                    BooklistItem.thread_id.in_(removed_thread_ids),  # type: ignore
                )
            )

            # 扣减各个受影响书单的 item_count
            whens = {
                bid: func.greatest(0, Booklist.item_count - count)
                for bid, count in booklist_decrements.items()
            }
            case_stmt = case(whens, value=Booklist.id, else_=Booklist.item_count)

            await self.session.execute(
                update(Booklist)
                .where(Booklist.id.in_(booklist_decrements.keys()))  # type: ignore
                .values(item_count=case_stmt)
            )

            await self.session.commit()

            return BatchRemoveResult(
                removed_ids=removed_thread_ids,
                removed_count=len(removed_thread_ids),
                not_found_count=len(target_ids) - len(removed_thread_ids),
            )
        else:
            # target_type == 2 (书单) , 操作 UserCollection
            # 找出实际存在的收藏
            select_stmt = select(UserCollection.target_id).where(
                and_(
                    UserCollection.user_id == user_id,
                    UserCollection.target_type == target_type,
                    UserCollection.target_id.in_(target_ids),  # type: ignore
                )
            )
            result = await self.session.execute(select_stmt)
            ids_to_remove = list(result.scalars().all())

            if not ids_to_remove:
                return BatchRemoveResult(
                    removed_ids=[], removed_count=0, not_found_count=len(target_ids)
                )

            # 删除这些收藏
            delete_stmt = delete(UserCollection).where(
                and_(
                    UserCollection.user_id == user_id,
                    UserCollection.target_type == target_type,
                    UserCollection.target_id.in_(ids_to_remove),  # type: ignore
                )
            )
            await self.session.execute(delete_stmt)
            await self.session.commit()

            return BatchRemoveResult(
                removed_ids=ids_to_remove,
                removed_count=len(ids_to_remove),
                not_found_count=len(target_ids) - len(ids_to_remove),
            )

    async def get_followed_not_collected_threads(
        self, user_id: int, page: int, per_page: int
    ) -> Tuple[List[Thread], int]:
        """获取用户已关注但未收藏的帖子"""
        offset = (page - 1) * per_page

        # 子查询：获取用户已收藏的帖子ID（通过 owner_id 查询用户的所有书单项）
        collected_subquery = select(BooklistItem.thread_id).where(
            BooklistItem.owner_id == user_id
        )

        # 主查询（仅活跃关注）
        base_query = (
            select(Thread)
            .join(ThreadFollow, Thread.thread_id == ThreadFollow.thread_id)  # type: ignore
            .where(
                ThreadFollow.user_id == user_id,
                ThreadFollow.active_flag,  # type: ignore
                Thread.thread_id.not_in(collected_subquery),  # type: ignore
            )
        )

        # 计数
        count_stmt = select(func.count()).select_from(base_query.alias("sub"))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar_one_or_none() or 0

        # 获取数据
        data_stmt = (
            base_query.order_by(desc(ThreadFollow.followed_at))
            .offset(offset)
            .limit(per_page)
            .options(selectinload(Thread.tags))
        )
        data_result = await self.session.execute(data_stmt)
        threads = data_result.scalars().all()

        return list(threads), total_count

    async def get_collected_targets(
        self,
        user_id: int,
        target_type: CollectionType,
        page: int,
        per_page: int,
        model_class: Type[T],
    ) -> Tuple[List[T], int]:
        """
        获取用户已收藏的特定类型目标列表（分页）。

        Args:
            user_id: 用户ID
            target_type: 目标类型
            page: 页码（从1开始）
            per_page: 每页数量
            model_class: 目标模型类（Thread 或 Booklist）

        Returns:
            包含目标列表和总数的元组。

        Raises:
            AttributeError: 当 model_class 不是 Thread 或 Booklist 时。
        """
        offset = (page - 1) * per_page
        if target_type == CollectionType.THREAD:
            # 使用 group_by 按帖子 PK 去重，以防多书单同一帖子引发排序和分页爆炸
            base_query = (
                select(Thread)
                .join(BooklistItem, Thread.thread_id == BooklistItem.thread_id)  # type: ignore
                .where(BooklistItem.owner_id == user_id)
                .group_by(Thread.id)  # type: ignore
            )
            # 排序：按该帖子被加入任意书单的“最新时间”倒序
            sort_order = desc(func.max(BooklistItem.created_at))
        else:
            # 书单类型，操作 UserCollection
            join_on_condition = None
            if model_class is Thread:
                join_on_condition = Thread.thread_id == UserCollection.target_id
            elif model_class is Booklist:
                join_on_condition = Booklist.id == UserCollection.target_id
            else:
                raise AttributeError(
                    f"Model {model_class.__name__} does not have a recognized primary key for joining."
                )

            base_query = (
                select(model_class)
                .join(
                    UserCollection,
                    and_(
                        join_on_condition,
                        UserCollection.target_type == target_type,
                    ),
                )
                .where(UserCollection.user_id == user_id)
            )
            # 排序：按收藏时间倒序
            sort_order = desc(UserCollection.created_at)

        # 计数
        count_stmt = select(func.count()).select_from(base_query.alias("sub"))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar_one_or_none() or 0

        # 获取数据
        data_stmt = base_query.order_by(sort_order).offset(offset).limit(per_page)
        if model_class is Thread:
            data_stmt = data_stmt.options(selectinload(Thread.tags))
        data_result = await self.session.execute(data_stmt)
        targets = data_result.scalars().all()

        return list(targets), total_count

    async def get_collected_target_ids(
        self, user_id: int, target_type: CollectionType, target_ids: Sequence[int]
    ) -> set[int]:
        """
        从给定的目标ID列表中，找出指定用户已收藏的目标ID。

        Args:
            user_id: 用户ID
            target_type: 目标类型
            target_ids: 要检查的目标ID列表

        Returns:
            一个包含已收藏目标ID的集合。
        """
        if not target_ids:
            return set()

        if target_type == CollectionType.THREAD:
            # 帖子类型，通过 owner_id 查询用户的所有书单项
            statement = select(BooklistItem.thread_id).where(
                and_(
                    BooklistItem.owner_id == user_id,
                    BooklistItem.thread_id.in_(target_ids),  # type: ignore
                )
            )
            result = await self.session.execute(statement)
            return set(result.scalars().all())
        else:
            # 书单类型，查询 UserCollection
            statement = select(UserCollection.target_id).where(
                and_(
                    UserCollection.user_id == user_id,
                    UserCollection.target_type == target_type,
                    UserCollection.target_id.in_(target_ids),  # type: ignore
                )
            )
            result = await self.session.execute(statement)
            return set(result.scalars().all())
