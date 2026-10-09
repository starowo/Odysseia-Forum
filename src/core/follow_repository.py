import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from dto.author_dto import AuthorDTO
from dto.followed_thread_record_dto import FollowedThreadRecordDTO
from dto.thread_dto import ThreadDTO
from models import Thread, ThreadFollow

logger = logging.getLogger(__name__)


class ThreadFollowRepository:
    """关注列表服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_follow(
        self, user_id: int, thread_id: int, auto_view: bool = False
    ) -> bool:
        """
        添加关注。若已存在非活跃记录则重新激活。

        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID
            auto_view: 是否自动标记为已查看（用于用户主动加入的情况）

        Returns:
            是否成功添加/重新激活（已存在且活跃时返回False）
        """
        try:
            # 检查是否已有记录（无论活跃与否）
            statement = select(ThreadFollow).where(
                and_(
                    ThreadFollow.user_id == user_id,  # type: ignore
                    ThreadFollow.thread_id == thread_id,  # type: ignore
                )
            )
            result = await self.session.execute(statement)
            existing = result.scalar_one_or_none()

            now = datetime.now(timezone.utc).replace(tzinfo=None)

            if existing:
                if existing.active_flag:
                    logger.debug(f"用户 {user_id} 已关注帖子 {thread_id}")
                    return False
                # 重新激活非活跃记录
                existing.active_flag = True
                existing.followed_at = now
                existing.last_viewed_at = now if auto_view else existing.last_viewed_at
                self.session.add(existing)
                await self.session.commit()
                logger.debug(f"用户 {user_id} 重新激活对帖子 {thread_id} 的关注")
                return True

            # 创建关注记录
            follow = ThreadFollow(
                user_id=user_id,
                thread_id=thread_id,
                followed_at=now,
                last_viewed_at=now if auto_view else None,
            )

            self.session.add(follow)
            await self.session.commit()

            logger.debug(f"用户 {user_id} 已关注帖子 {thread_id}")
            return True

        except Exception as e:
            logger.error(f"添加关注失败: {e}", exc_info=True)
            await self.session.rollback()
            return False

    async def batch_add_follows(self, thread_id: int, user_ids: List[int]) -> int:
        """
        批量添加关注（用于首次检测到帖子时）。
        已存在但非活跃的记录会被重新激活。

        Args:
            thread_id: 帖子Discord ID
            user_ids: 用户Discord ID列表

        Returns:
            成功添加/重新激活的数量
        """
        if not user_ids:
            return 0

        try:
            # 查询已存在的关注记录（无论活跃与否）
            statement = select(ThreadFollow).where(
                and_(
                    ThreadFollow.thread_id == thread_id,  # type: ignore[arg-type]
                    col(ThreadFollow.user_id).in_(user_ids),
                )
            )
            result = await self.session.execute(statement)
            existing_follows = result.scalars().all()

            existing_map = {f.user_id: f for f in existing_follows}
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # 重新激活非活跃的已有记录
            reactivated = 0
            for follow in existing_follows:
                if not follow.active_flag:
                    follow.active_flag = True
                    follow.followed_at = now
                    self.session.add(follow)
                    reactivated += 1

            # 过滤出需要新增的用户
            new_user_ids = [uid for uid in user_ids if uid not in existing_map]

            # 批量创建新关注记录
            if new_user_ids:
                follows = [
                    ThreadFollow(
                        user_id=user_id,
                        thread_id=thread_id,
                        followed_at=now,
                        last_viewed_at=None,  # 首次添加时不标记为已查看
                    )
                    for user_id in new_user_ids
                ]
                self.session.add_all(follows)

            await self.session.commit()

            total = len(new_user_ids) + reactivated
            if total:
                logger.debug(
                    f"为帖子 {thread_id} 批量处理关注: "
                    f"新增 {len(new_user_ids)}, 重新激活 {reactivated}"
                )
            return total

        except Exception as e:
            logger.error(f"批量添加关注失败: {e}", exc_info=True)
            await self.session.rollback()
            return 0

    async def remove_follow(self, user_id: int, thread_id: int) -> bool:
        """
        取消关注（软删除：设置 active_flag=False）

        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID

        Returns:
            是否成功取消
        """
        try:
            # 仅标记活跃关注为非活跃，已非活跃的不重复操作
            stmt = (
                update(ThreadFollow)
                .where(
                    and_(
                        ThreadFollow.user_id == user_id,  # type: ignore[arg-type]
                        ThreadFollow.thread_id == thread_id,  # type: ignore[arg-type]
                        ThreadFollow.active_flag,  # type: ignore[arg-type]
                    )
                )
                .values(active_flag=False)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                logger.debug(f"用户 {user_id} 已取消关注帖子 {thread_id}")
                return True
            else:
                logger.debug(f"用户 {user_id} 未关注帖子 {thread_id}")
                return False

        except Exception as e:
            logger.error(f"取消关注失败: {e}", exc_info=True)
            await self.session.rollback()
            return False

    async def batch_mark_inactive(self, thread_id: int, user_ids: List[int]) -> int:
        """
        批量将关注标记为过去关注（非活跃）。

        Args:
            thread_id: 帖子Discord ID
            user_ids: 用户Discord ID列表

        Returns:
            受影响的行数
        """
        if not user_ids:
            return 0

        try:
            stmt = (
                update(ThreadFollow)
                .where(
                    and_(
                        ThreadFollow.thread_id == thread_id,  # type: ignore[arg-type]
                        col(ThreadFollow.user_id).in_(user_ids),
                        ThreadFollow.active_flag,  # type: ignore[arg-type]
                    )
                )
                .values(active_flag=False)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()

            count = result.rowcount
            logger.debug(f"帖子 {thread_id}: 已将 {count} 个关注标记为非活跃")
            return count

        except Exception as e:
            logger.error(f"批量标记非活跃失败: {e}", exc_info=True)
            await self.session.rollback()
            return 0

    async def update_last_viewed(
        self, user_id: int, thread_id: Optional[int] = None
    ) -> bool:
        """
        更新最后查看时间

        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID，如果为None则更新所有关注

        Returns:
            是否成功更新
        """
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            if thread_id is not None:
                # 更新单个帖子
                statement = select(ThreadFollow).where(
                    and_(
                        ThreadFollow.user_id == user_id,  # type: ignore
                        ThreadFollow.thread_id == thread_id,  # type: ignore
                    )
                )
                result = await self.session.execute(statement)
                follow = result.scalar_one_or_none()

                if follow:
                    follow.last_viewed_at = now
                    self.session.add(follow)
                    await self.session.commit()
                    logger.debug(f"已更新用户 {user_id} 对帖子 {thread_id} 的查看时间")
                    return True
                else:
                    logger.warning(f"用户 {user_id} 未关注帖子 {thread_id}")
                    return False
            else:
                # 更新所有关注
                statement = select(ThreadFollow).where(ThreadFollow.user_id == user_id)  # type: ignore
                result = await self.session.execute(statement)
                follows = result.scalars().all()

                for follow in follows:
                    follow.last_viewed_at = now
                    self.session.add(follow)

                await self.session.commit()
                logger.debug(f"已更新用户 {user_id} 的所有关注查看时间")
                return True

        except Exception as e:
            logger.error(f"更新查看时间失败: {e}", exc_info=True)
            await self.session.rollback()
            return False

    async def get_user_follows(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        active_flag: Optional[bool] = None,
        channel_ids: Optional[List[int]] = None,
    ) -> tuple[List[FollowedThreadRecordDTO], int]:
        """
        获取用户关注的帖子列表

        Args:
            user_id: 用户Discord ID
            limit: 返回数量限制
            offset: 偏移量
            active_flag: 筛选关注状态（None=全部, True=当前关注, False=过去关注）
            channel_ids: 频道ID列表（可选，用于按频道筛选）

        Returns:
            (帖子列表, 总数)
        """
        try:
            # 构建查询，使用selectinload加载tags，joinedload加载author
            from sqlalchemy.orm import joinedload, selectinload

            statement = (
                select(Thread, ThreadFollow)
                .join(ThreadFollow, Thread.thread_id == ThreadFollow.thread_id)  # type: ignore[arg-type]
                .where(ThreadFollow.user_id == user_id)  # type: ignore[arg-type]
                .options(
                    selectinload(Thread.tags),  # type: ignore[arg-type]
                    joinedload(Thread.author),  # type: ignore[arg-type]
                )
                .order_by(ThreadFollow.followed_at.desc())  # type: ignore[attr-defined]
                .limit(limit)
                .offset(offset)
            )

            if active_flag is not None:
                statement = statement.where(ThreadFollow.active_flag == active_flag)  # type: ignore[arg-type]

            if channel_ids is not None:
                statement = statement.where(Thread.channel_id.in_(channel_ids))  # type: ignore[arg-type]

            result = await self.session.execute(statement)
            rows = result.all()

            # 统计总数
            count_statement = (
                select(func.count())
                .select_from(ThreadFollow)
                .where(ThreadFollow.user_id == user_id)  # type: ignore[arg-type]
            )
            if active_flag is not None:
                count_statement = count_statement.where(
                    ThreadFollow.active_flag == active_flag  # type: ignore[arg-type]
                )
            if channel_ids is not None:
                count_statement = count_statement.join(
                    Thread,
                    ThreadFollow.thread_id == Thread.thread_id,  # type: ignore[arg-type]
                ).where(Thread.channel_id.in_(channel_ids))  # type: ignore[arg-type]
            count_result = await self.session.execute(count_statement)
            total = count_result.scalar() or 0

            results: list[FollowedThreadRecordDTO] = []
            for thread, follow in rows:
                results.append(
                    FollowedThreadRecordDTO(
                        thread=ThreadDTO.from_orm(thread),
                        author=AuthorDTO.from_orm(thread.author)
                        if thread.author
                        else None,
                        followed_at=follow.followed_at,
                        last_viewed_at=follow.last_viewed_at,
                        active_flag=follow.active_flag,
                    )
                )

            return results, total

        except Exception as e:
            logger.error(f"获取关注列表失败: {e}", exc_info=True)
            return [], 0

    async def get_unread_count(self, user_id: int) -> int:
        """
        获取用户未读更新的数量（仅统计活跃关注）

        Args:
            user_id: 用户Discord ID

        Returns:
            未读更新数量
        """
        try:
            # 查询有更新且未查看的帖子数量，仅活跃关注
            statement = (
                select(func.count())
                .select_from(ThreadFollow)
                .join(Thread, ThreadFollow.thread_id == Thread.thread_id)  # type: ignore[arg-type]
                .where(
                    and_(
                        ThreadFollow.user_id == user_id,  # type: ignore[arg-type]
                        ThreadFollow.active_flag,  # type: ignore[arg-type]
                        Thread.latest_update_at.isnot(None),  # type: ignore[attr-defined]
                        # 未查看 或 更新时间晚于查看时间
                        (
                            (ThreadFollow.last_viewed_at.is_(None))  # type: ignore[attr-defined]
                            | (Thread.latest_update_at > ThreadFollow.last_viewed_at)  # type: ignore[operator]
                        ),
                    )
                )
            )

            result = await self.session.execute(statement)
            count = result.scalar() or 0

            return count

        except Exception as e:
            logger.error(f"获取未读数量失败: {e}", exc_info=True)
            return 0

    async def is_following(
        self, user_id: int, thread_id: int, active_only: bool = True
    ) -> bool:
        """
        检查用户是否关注了某个帖子

        Args:
            user_id: 用户Discord ID
            thread_id: 帖子Discord ID
            active_only: 是否仅检查活跃关注（默认True，过去关注不算"正在关注"）

        Returns:
            是否关注
        """
        try:
            conditions = [
                ThreadFollow.user_id == user_id,  # type: ignore[arg-type]
                ThreadFollow.thread_id == thread_id,  # type: ignore[arg-type]
            ]
            if active_only:
                conditions.append(ThreadFollow.active_flag)  # type: ignore[arg-type]

            statement = select(ThreadFollow).where(and_(*conditions))  # type: ignore[arg-type]
            result = await self.session.execute(statement)
            follow = result.scalar_one_or_none()

            return follow is not None

        except Exception as e:
            logger.error(f"检查关注状态失败: {e}", exc_info=True)
            return False
