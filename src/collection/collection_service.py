import logging
from typing import List, Dict, Any, Tuple, Sequence, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, and_, select, func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.sqlite import insert
from shared.models.booklist import Booklist
from shared.models.user_collection import UserCollection
from shared.models.thread_follow import ThreadFollow
from shared.models.thread import Thread
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
    ) -> Dict[str, Any]:
        """
        批量添加收藏（同一类型）。

        Args:
            user_id: 用户ID
            target_type: 目标类型
            target_ids: 目标ID列表

        Returns:
            包含成功添加数量和重复数量的字典。
        """
        if not target_ids:
            return {"added": 0, "duplicates": 0}

        # 构建插入值列表
        values = [
            {"user_id": user_id, "target_type": target_type, "target_id": tid}
            for tid in target_ids
        ]
        stmt = (
            insert(UserCollection)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=["user_id", "target_type", "target_id"]
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        # 获取插入的行数
        added = result.rowcount if result.rowcount is not None else 0
        duplicates = len(target_ids) - added
        return {"added": added, "duplicates": duplicates}

    async def remove_collections(
        self, user_id: int, target_type: int, target_ids: List[int]
    ) -> Dict[str, Any]:
        """
        批量移除收藏（同一类型）。

        Args:
            user_id: 用户ID
            target_type: 目标类型
            target_ids: 目标ID列表

        Returns:
            包含成功移除数量和未找到数量的字典。
        """
        if not target_ids:
            return {"removed": 0, "not_found": 0}

        statement = delete(UserCollection).where(
            and_(
                UserCollection.user_id == user_id,
                UserCollection.target_type == target_type,
                UserCollection.target_id.in_(target_ids),  # type: ignore
            )
        )
        result = await self.session.execute(statement)
        await self.session.commit()
        removed = result.rowcount
        not_found = len(target_ids) - removed
        return {"removed": removed, "not_found": not_found}

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
            join_on_condition = model_class.id == UserCollection.target_id
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
            base_query.order_by(desc(UserCollection.create_at))
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
