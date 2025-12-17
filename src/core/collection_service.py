import logging
from typing import List, Sequence, Tuple, Type, TypeVar

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, delete, desc, func, select

from collection.dto import BatchAddResult, BatchRemoveResult
from models import Booklist, Thread, ThreadFollow, UserCollection
from shared.enum.collection_type import CollectionType

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CollectionService:
    """封装与用户收藏相关的数据库操作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_collection(
        self, user_id: int, target_type: int, target_id: int
    ) -> bool:
        """
        为用户添加一个收藏

        Returns:
            bool: 如果是新收藏则返回 True，如果已存在则返回 False
        """
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
            # 触发了 UNIQUE 约束
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
        statement = delete(UserCollection).where(
            and_(
                UserCollection.user_id == user_id,
                UserCollection.target_type == target_type,
                UserCollection.target_id == target_id,
            )
        )
        result = await self.session.execute(statement)
        await self.session.commit()

        if result.rowcount > 0:
            return True
        else:
            logger.debug(
                f"用户 {user_id} 尝试移除不存在的收藏 {target_type}:{target_id}"
            )
            return False

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
            stmt = insert(UserCollection).values(values)
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

        # 子查询：获取用户已收藏的帖子ID（仅限帖子类型）
        collected_subquery = select(UserCollection.target_id).where(
            and_(
                UserCollection.user_id == user_id,
                UserCollection.target_type == CollectionType.THREAD,
            )
        )

        # 主查询
        base_query = (
            select(Thread)
            .join(ThreadFollow, Thread.thread_id == ThreadFollow.thread_id)  # type: ignore
            .where(
                ThreadFollow.user_id == user_id,
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
            target_type: 目标类型（CollectionType.THREAD 或 CollectionType.BOOKLIST）
            page: 页码（从1开始）
            per_page: 每页数量
            model_class: 目标模型类（Thread 或 Booklist）

        Returns:
            包含目标列表和总数的元组。

        Raises:
            AttributeError: 当 model_class 不是 Thread 或 Booklist 时。
        """
        offset = (page - 1) * per_page

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

        # 计数
        count_stmt = select(func.count()).select_from(base_query.alias("sub"))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar_one_or_none() or 0

        # 获取数据
        data_stmt = (
            base_query.order_by(desc(UserCollection.created_at))
            .offset(offset)
            .limit(per_page)
        )
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

        statement = select(UserCollection.target_id).where(
            and_(
                UserCollection.user_id == user_id,
                UserCollection.target_type == target_type,
                UserCollection.target_id.in_(target_ids),  # type: ignore
            )
        )
        result = await self.session.execute(statement)
        return set(result.scalars().all())
