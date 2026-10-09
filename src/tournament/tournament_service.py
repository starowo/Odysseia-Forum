"""赛事业务逻辑服务层"""

import logging
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from api.v1.schemas.booklist import BooklistItemUpdateRequest
from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData
from core.booklist_sort_constants import DEFAULT_SORT_METHOD, DEFAULT_SORT_ORDER
from api.v1.schemas.tournament.tournament_create_request import TournamentCreateRequest
from api.v1.schemas.tournament.tournament_item_update_request import (
    TournamentItemUpdateRequest,
)
from api.v1.schemas.tournament.tournament_items_add_request import (
    TournamentItemAddData,
)
from api.v1.schemas.tournament.tournament_update_request import TournamentUpdateRequest
from core.booklist_item_repository import BooklistItemRepository
from core.booklist_repository import BooklistRepository
from models.booklist import Booklist
from models.booklist_item import BooklistItem
from shared.enum.cache_keys import CacheKeys

logger = logging.getLogger(__name__)


class TournamentService:
    """赛事业务逻辑，基于书单基础设施，绕过 owner 校验以支持 BOT 调用"""

    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.booklist_repo = BooklistRepository(session)
        self.booklist_item_repo = BooklistItemRepository(session)
        self._redis = redis_client

    async def create_or_get_tournament(
        self, request: TournamentCreateRequest
    ) -> Tuple[Booklist, bool]:
        """幂等创建赛事书单。返回 (booklist, created)"""
        existing = await self.booklist_repo.get_booklist_by_tournament_channel_id(
            request.tournament_channel_id
        )
        if existing:
            return existing, False

        try:
            booklist = await self.booklist_repo.create_booklist(
                owner_id=request.owner_id,
                title=request.title,
                description=request.description,
                cover_image_url=request.cover_image_url,
                is_public=request.is_public,
                is_anonymous=False,
                default_sort_method=DEFAULT_SORT_METHOD.value,
                default_sort_order=DEFAULT_SORT_ORDER.value,
                is_tournament=True,
                tournament_channel_id=request.tournament_channel_id,
            )
            logger.info(
                f"赛事书单创建: booklist_id={booklist.id}, channel_id={request.tournament_channel_id}"
            )
            return booklist, True
        except IntegrityError:
            await self.session.rollback()
            existing = await self.booklist_repo.get_booklist_by_tournament_channel_id(
                request.tournament_channel_id
            )
            if existing:
                return existing, False
            raise

    async def add_items(
        self, tournament_channel_id: int, items: List[TournamentItemAddData]
    ) -> List[BooklistItem]:
        """向赛事书单添加帖子（BOT 调用，不校验 owner）"""
        booklist = await self._get_tournament(tournament_channel_id)

        converted = []
        for item in items:
            converted.append(
                BooklistItemAddData(
                    thread_id=item.thread_id,
                    comment=item.comment,
                    display_order=None,
                    tournament_participated_at=item.tournament_participated_at,
                )
            )

        result = await self.booklist_repo.add_threads_to_booklist(
            booklist.id, converted
        )  # type: ignore[arg-type]
        await self._invalidate_thread_cache([item.thread_id for item in items])
        return result

    async def remove_items(
        self, tournament_channel_id: int, thread_ids: List[int]
    ) -> int:
        """从赛事书单移除帖子（BOT 调用，不校验 owner）"""
        booklist = await self._get_tournament(tournament_channel_id)
        result = await self.booklist_repo.remove_threads_from_booklist(
            booklist.id,
            thread_ids,  # type: ignore[arg-type]
        )
        await self._invalidate_thread_cache(thread_ids)
        return result

    async def update_item(
        self,
        tournament_channel_id: int,
        thread_id: int,
        update_data: TournamentItemUpdateRequest,
    ) -> Optional[BooklistItem]:
        """更新赛事书单中的帖子信息（BOT 调用，不校验 owner）"""
        booklist = await self._get_tournament(tournament_channel_id)

        converted = BooklistItemUpdateRequest(
            comment=update_data.comment,
            display_order=None,
            tournament_participated_at=update_data.tournament_participated_at,
        )
        return await self.booklist_item_repo.update_booklist_item(
            booklist.id,
            thread_id,
            converted,  # type: ignore[arg-type]
        )

    async def delete_tournament(self, tournament_channel_id: int) -> bool:
        """删除赛事书单及其所有关联帖子"""
        booklist = await self._get_tournament(tournament_channel_id)
        # 先查出所有关联的 thread_id 用于缓存失效
        items_stmt = select(BooklistItem.thread_id).where(
            BooklistItem.booklist_id == booklist.id
        )
        item_rows = (await self.session.execute(items_stmt)).all()
        affected_ids = [row[0] for row in item_rows]
        result = await self.booklist_repo.delete_booklist(booklist.id)  # type: ignore[arg-type]
        await self._invalidate_thread_cache(affected_ids)
        return result

    async def update_tournament(
        self,
        tournament_channel_id: int,
        request: TournamentUpdateRequest,
    ) -> Booklist:
        """更新赛事书单元信息"""
        booklist = await self._get_tournament(tournament_channel_id)

        updated = await self.booklist_repo.update_booklist(
            booklist.id,  # type: ignore[arg-type]
            title=request.title,
            description=request.description,
            cover_image_url=request.cover_image_url,
            is_public=request.is_public,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新赛事书单失败",
            )
        return updated

    async def _invalidate_thread_cache(self, thread_ids: List[int]) -> None:
        """删除指定帖子的赛事信息 Redis 缓存"""
        if not self._redis or not thread_ids:
            return

        keys = [CacheKeys.TOURNAMENT_THREAD.format(thread_id=tid) for tid in thread_ids]
        try:
            await self._redis.delete(*keys)
        except Exception:
            logger.warning("删除赛事缓存失败", exc_info=True)

    async def _get_tournament(self, tournament_channel_id: int) -> Booklist:
        booklist = await self.booklist_repo.get_booklist_by_tournament_channel_id(
            tournament_channel_id
        )
        if not booklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"赛事书单不存在: channel_id={tournament_channel_id}",
            )
        if not booklist.is_tournament:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="该书单不是赛事书单，无法通过赛事接口操作",
            )
        return booklist
