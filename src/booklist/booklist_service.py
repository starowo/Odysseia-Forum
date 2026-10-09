import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData
from core.booklist_repository import BooklistRepository
from core.redis_trend_service import RedisTrendService
from core.thread_repository import ThreadRepository
from dto.booklist_item_dto import BooklistItemDTO
from dto.booklist_items_sync_dto import BooklistItemsSyncDTO
from models import Booklist, BooklistItem, Thread
from shared.enum import ConstantEnum

logger = logging.getLogger(__name__)

# 由 api_main.py 注入的发布配置
_booklist_publish_base_url: str = ""
_booklist_publish_api_key: str = ""


async def _delayed_publish_sync(booklist_id: int, delay: float = 5.0) -> None:
    """等待 delay 秒后，若书单已发布则重新同步 embed 到 Discord"""
    if not _booklist_publish_base_url:
        return
    await asyncio.sleep(delay)
    try:
        from booklist.booklist_publish_service import BooklistPublishService
        from shared.database import AsyncSessionFactory

        async with AsyncSessionFactory() as session:
            service = BooklistPublishService(
                session,
                base_url=_booklist_publish_base_url,
                api_key=_booklist_publish_api_key,
            )
            await service.sync_published_booklist(booklist_id)
    except Exception:
        logger.warning("延迟同步书单 %d 的发布内容失败", booklist_id, exc_info=True)


class BooklistService:
    """书单业务逻辑服务层，负责协调书单表与帖子表的数据互通"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.booklist_repo = BooklistRepository(session)
        self.thread_repo = ThreadRepository(session)

    async def add_threads(
        self, user_id: int, booklist_id: int, items: List[BooklistItemAddData]
    ) -> List[BooklistItemDTO]:
        """
        将帖子批量加入书单，并同步帖子的被收藏次数（跨书单去重）

        返回 DTO 列表，确保在 session 外也能安全访问。
        """
        # 权限校验：确认书单存在且属于当前用户
        booklist = await self.booklist_repo.get_booklist(booklist_id)
        if not booklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
            )
        if booklist.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此书单"
            )

        # 提取并转换帖子 ID 列表
        thread_ids = [int(item.thread_id) for item in items]
        if not thread_ids:
            return []

        # 查询这些帖子是否已存在于该用户的其他书单中，用于后续净增量计算
        existing_anywhere = await self.booklist_repo.get_threads_in_users_booklists(
            user_id, thread_ids
        )

        # 执行书单添加操作（内部会 commit + refresh，返回 ORM 对象）
        added_items = await self.booklist_repo.add_threads_to_booklist(
            booklist_id, items
        )

        if not added_items:
            return []

        # 在第二次 commit 之前立即转为 DTO，避免 update_collection_counts
        # 内部的 commit 过期 ORM 对象导致 MissingGreenlet
        item_dtos = [BooklistItemDTO.from_orm(item) for item in added_items]
        added_thread_ids = [dto.thread_id for dto in item_dtos]
        net_new_ids = list(
            {tid for tid in added_thread_ids if tid not in existing_anywhere}
        )

        if net_new_ids:
            # 更新数据库中的帖子全局收藏数（内部会 commit，但 DTO 不受影响）
            await self.thread_repo.update_collection_counts(net_new_ids, 1)

            # 同步 Redis 飙升榜数据：仅统计近期发布的帖子，防止老帖屠榜
            threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                days=ConstantEnum.STATISTICS_THRESHOLD_DAYS.value
            )
            stmt = select(Thread.thread_id, Thread.channel_id).where(
                Thread.thread_id.in_(net_new_ids),  # type: ignore
                Thread.created_at >= threshold,
            )
            valid_threads = (await self.session.execute(stmt)).all()

            if valid_threads:
                trend_service = RedisTrendService()
                for tid, channel_id in valid_threads:
                    await trend_service.record_increment(
                        "collection", int(tid), int(channel_id), count=1
                    )

        # 触发发布内容同步（异步后台，5 秒延迟）
        asyncio.create_task(_delayed_publish_sync(booklist_id))

        return item_dtos

    async def remove_threads(
        self, user_id: int, booklist_id: int, thread_ids: List[int]
    ) -> int:
        """
        从书单批量移除帖子，并同步帖子的被收藏次数（跨书单去重）
        """
        # 权限校验：确认书单存在且属于当前用户
        booklist = await self.booklist_repo.get_booklist(booklist_id)
        if not booklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="书单不存在"
            )
        if booklist.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此书单"
            )

        if not thread_ids:
            return 0

        # 执行书单移除操作
        deleted_count = await self.booklist_repo.remove_threads_from_booklist(
            booklist_id, thread_ids
        )

        if deleted_count > 0:
            # 检查移除后这些帖子是否仍存在于该用户的其他书单中
            still_existing = await self.booklist_repo.get_threads_in_users_booklists(
                user_id, thread_ids
            )

            # 筛选出全书单级别的净减帖子（从所有书单中彻底移除）
            net_removed_ids = list(set(thread_ids) - still_existing)

            if net_removed_ids:
                # 更新数据库中的帖子全局收藏数（仅递减净减项）
                await self.thread_repo.update_collection_counts(net_removed_ids, -1)

        # 触发发布内容同步（异步后台，5 秒延迟）
        if deleted_count > 0:
            asyncio.create_task(_delayed_publish_sync(booklist_id))

        return deleted_count

    async def sync_thread_in_booklists(
        self,
        user_id: int,
        thread_id: int,
        scope_booklist_ids: List[int],
        target_booklist_ids: List[int],
        comment: str | None = None,
    ):
        """
        批量同步一个帖子在用户多个书单中的存在性。

        - scope_booklist_ids：操作范围（必须全属于当前用户）
        - target_booklist_ids：操作后应包含该帖子的书单（必须是 scope 的子集）
        - comment：应用于目标书单项的推荐语
        """
        # 1. 校验 scope 不能为空
        if not scope_booklist_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="scope_booklist_ids 不能为空",
            )

        # 2. 校验 target ⊆ scope
        target_set = set(target_booklist_ids)
        scope_set = set(scope_booklist_ids)
        if not target_set.issubset(scope_set):
            outside = list(target_set - scope_set)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"target_booklist_ids 包含不在 scope 中的书单: {outside}",
            )

        # 3. 校验所有权：所有 scope 书单必须属于当前用户
        stmt = (
            select(Booklist.id, Booklist.owner_id).where(
                Booklist.id.in_(list(scope_set))
            )  # type: ignore
        )
        booklist_rows = (await self.session.execute(stmt)).all()
        found_ids = {row[0] for row in booklist_rows}

        for row in booklist_rows:
            if row[1] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"书单 {row[0]} 不属于当前用户",
                )

        # 检查是否有 scope 中书单不存在
        missing = scope_set - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"书单不存在: {list(missing)}",
            )

        # 4. 查询 scope 中哪些书单已包含该帖子
        existing_stmt = select(BooklistItem.booklist_id).where(
            BooklistItem.thread_id == thread_id,  # type: ignore
            BooklistItem.booklist_id.in_(list(scope_set)),  # type: ignore
        )
        existing_rows = await self.session.execute(existing_stmt)
        existing_set = set(existing_rows.scalars().all())

        # 记录操作前用户任意书单是否已收藏，避免局部 scope 导致重复计数趋势。
        collected_before = await self.booklist_repo.get_threads_in_users_booklists(
            user_id, [thread_id]
        )

        # 5. 计算 add_to / remove_from / unchanged
        add_to = list(target_set - existing_set)
        remove_from = list(existing_set - target_set)
        unchanged = list(scope_set - set(add_to) - set(remove_from))

        # 6. 执行添加和删除
        added_ids = []
        removed_ids = []
        if add_to:
            added_ids = await self.booklist_repo.add_thread_to_booklists(
                thread_id, add_to, user_id, comment
            )
        if remove_from:
            removed_ids = await self.booklist_repo.remove_thread_from_booklists(
                thread_id, remove_from
            )

        # 已有目标项需要单独同步推荐语，新增项已在插入时写入
        existing_target_ids = target_set & existing_set
        if comment is not None and existing_target_ids:
            await self.booklist_repo.update_thread_comment_in_booklists(
                thread_id, list(existing_target_ids), comment
            )

        # 7. 跨域同步 Thread.collection_count（净增减）
        # 查询操作前：thread 是否已在用户任何书单中
        had_before = bool(collected_before)

        # 查询操作后：thread 是否仍在用户任何书单中
        still_exists = await self.booklist_repo.get_threads_in_users_booklists(
            user_id, [thread_id]
        )
        has_after = bool(still_exists)

        if not had_before and has_after:
            # 用户首次收藏此帖
            await self.thread_repo.update_collection_counts([thread_id], 1)

            # Redis 飙升榜
            threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                days=ConstantEnum.STATISTICS_THRESHOLD_DAYS.value
            )
            check_stmt = select(Thread.thread_id, Thread.channel_id).where(
                Thread.thread_id == thread_id,  # type: ignore
                Thread.created_at >= threshold,
            )
            valid_thread = (await self.session.execute(check_stmt)).one_or_none()
            if valid_thread:
                trend_service = RedisTrendService()
                await trend_service.record_increment(
                    "collection",
                    thread_id,
                    int(valid_thread.channel_id),
                    count=1,
                )

        elif had_before and not has_after:
            # 用户完全取消收藏此帖
            await self.thread_repo.update_collection_counts([thread_id], -1)

        return BooklistItemsSyncDTO(
            thread_id=thread_id,
            added_to_booklist_ids=added_ids,
            removed_from_booklist_ids=removed_ids,
            unchanged_booklist_ids=unchanged,
        )
