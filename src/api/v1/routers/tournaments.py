"""赛事路由（BOT 机机通信）"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.v1.dependencies.security import require_api_key
from api.v1.schemas.base import PaginatedResponse
from api.v1.utils import BooklistItemEnricher
from api.v1.schemas.booklist import BooklistDetail, BooklistItemDetail
from api.v1.schemas.booklist.booklist_items_delete_request import (
    BooklistItemsDeleteRequest,
)
from api.v1.schemas.search.author_detail import AuthorDetail
from api.v1.schemas.tournament import (
    TournamentCreateRequest,
    TournamentCreateResponse,
    TournamentItemsAddRequest,
    TournamentItemUpdateRequest,
    TournamentUpdateRequest,
)
from core.author_repository import AuthorRepository
from core.booklist_item_repository import BooklistItemRepository
from core.booklist_repository import BooklistRepository
from core.cache_service import CacheService
from shared.database import AsyncSessionFactory
from tournament.tournament_service import TournamentService

logger = logging.getLogger(__name__)

# 全局变量，将在应用启动时由 bot_main.py 注入
cache_service_instance: CacheService | None = None


async def _fill_authors_for_booklists(
    session: Any, booklists: List[Any]
) -> Dict[int, Any]:
    """获取书单的作者映射（bot 场景不处理 Redis 过期队列）"""
    owner_ids = list(set(b.owner_id for b in booklists if getattr(b, "owner_id", None)))
    if not owner_ids:
        return {}

    author_repo = AuthorRepository(session)
    authors = await author_repo.get_authors_by_ids(owner_ids)
    return {a.id: a for a in authors}


def _apply_author_to_detail(
    detail: BooklistDetail, booklist: Any, author_map: Dict[int, Any]
) -> None:
    """为书单详情填充作者信息。bot 鉴权无 current_user，匿名时始终隐藏。"""
    if getattr(booklist, "is_anonymous", False):
        detail.owner_id = 0
        detail.author = AuthorDetail(
            id=0,
            name="匿名用户",
            global_name=None,
            display_name="匿名用户",
            avatar_url="https://cdn.discordapp.com/embed/avatars/0.png",
        )
    elif booklist.owner_id in author_map:
        detail.author = AuthorDetail.model_validate(
            author_map[booklist.owner_id], from_attributes=True
        )


router = APIRouter(prefix="/tournament", tags=["赛事"])


@router.post("/create", summary="创建赛事书单", response_model=TournamentCreateResponse)
async def create_tournament(
    request: TournamentCreateRequest,
    api_key: bool = Depends(require_api_key),
):
    """
    创建赛事书单。同一 tournament_channel_id 多次调用幂等返回已有书单。

    - **tournament_channel_id**: 赛事关联的 Discord 频道ID（唯一标识）
    - **owner_id**: 赛事举办者 Discord 用户ID（即书单 owner）
    - **title**: 赛事标题
    """
    try:
        async with AsyncSessionFactory() as session:
            service = TournamentService(
                session, redis_client=getattr(cache_service_instance, "_redis", None)
            )
            booklist, created = await service.create_or_get_tournament(request)

            return TournamentCreateResponse(
                message="赛事书单创建成功" if created else "赛事书单已存在",
                booklist_id=booklist.id,  # type: ignore[arg-type]
                title=booklist.title,
                tournament_channel_id=request.tournament_channel_id,
                created=created,
            )
    except Exception as e:
        logger.error(f"创建赛事书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建赛事书单失败",
        )


@router.get(
    "/list/page",
    summary="分页获取赛事书单列表",
    response_model=PaginatedResponse[BooklistDetail],
)
async def list_tournaments(
    tournament_channel_id: Optional[int] = Query(None, description="按赛事频道ID筛选"),
    sort_method: int = Query(
        4,
        description="排序方法: 1-帖子数, 2-浏览数, 3-收藏数, 4-创建时间, 5-最后更新时间",
    ),
    sort_order: str = Query(
        "desc", description="排序顺序: 'asc'(升序) 或 'desc'(降序)"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="每次请求返回的数量 (范围: 1-100)",
    ),
    offset: int = Query(default=0, ge=0, description="结果的偏移量，从0开始"),
    api_key: bool = Depends(require_api_key),
):
    """
    分页获取赛事书单列表。

    - **tournament_channel_id**: 按赛事频道ID筛选（可选）
    - **sort_method**: 排序方式 (1: 帖子数, 2: 浏览数, 3: 收藏数, 4: 创建时间, 5: 更新时间)
    - **sort_order**: 排序顺序 ('asc' 或 'desc')
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    try:
        async with AsyncSessionFactory() as session:
            service = BooklistRepository(session)
            booklists, total = await service.list_booklists(
                is_tournament=True,
                tournament_channel_id=tournament_channel_id,
                sort_method=sort_method,
                sort_order=sort_order,
                limit=limit,
                offset=offset,
            )

            author_map = await _fill_authors_for_booklists(session, booklists)

            results = []
            for b in booklists:
                detail = BooklistDetail.model_validate(b, from_attributes=True)
                _apply_author_to_detail(detail, b, author_map)
                results.append(detail)

        return PaginatedResponse(
            total=total, limit=limit, offset=offset, results=results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取赛事书单列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取赛事书单列表失败",
        )


@router.get(
    "/{tournament_channel_id}",
    summary="获取赛事书单详情",
    response_model=BooklistDetail,
)
async def get_tournament(
    tournament_channel_id: int,
    api_key: bool = Depends(require_api_key),
):
    """
    根据赛事频道ID获取赛事书单详情。

    - **tournament_channel_id**: 赛事频道ID
    """
    try:
        async with AsyncSessionFactory() as session:
            service = BooklistRepository(session)
            booklist = await service.get_booklist_by_tournament_channel_id(
                tournament_channel_id
            )
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="赛事书单不存在",
                )

            author_map = await _fill_authors_for_booklists(session, [booklist])
            detail = BooklistDetail.model_validate(booklist, from_attributes=True)
            _apply_author_to_detail(detail, booklist, author_map)

        return detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取赛事书单详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取赛事书单详情失败",
        )


@router.get(
    "/{tournament_channel_id}/items",
    summary="分页获取赛事项",
    response_model=PaginatedResponse[BooklistItemDetail],
)
async def get_tournament_items(
    tournament_channel_id: int,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="每次请求返回的数量 (范围: 1-100)",
    ),
    offset: int = Query(default=0, ge=0, description="结果的偏移量，从0开始"),
    api_key: bool = Depends(require_api_key),
):
    """
    分页获取赛事书单内的帖子详情。

    - **tournament_channel_id**: 赛事频道ID
    - **limit**: 返回数量
    - **offset**: 偏移量
    """
    try:
        async with AsyncSessionFactory() as session:
            booklist_service = BooklistRepository(session)
            booklist = await booklist_service.get_booklist_by_tournament_channel_id(
                tournament_channel_id
            )
            if not booklist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="赛事书单不存在",
                )

            item_service = BooklistItemRepository(session)
            items, total = await item_service.get_booklist_items_with_details(
                booklist_id=booklist.id,  # type: ignore[arg-type]
                default_sort_method=booklist.default_sort_method,
                default_sort_order=booklist.default_sort_order,
                limit=limit,
                offset=offset,
            )
            await BooklistItemEnricher.enrich(session, None, items)

        return PaginatedResponse(total=total, limit=limit, offset=offset, results=items)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取赛事项失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取赛事项失败",
        )


@router.post(
    "/{tournament_channel_id}/items/add",
    summary="向赛事添加参赛帖子",
)
async def add_tournament_items(
    tournament_channel_id: int,
    request: TournamentItemsAddRequest,
    api_key: bool = Depends(require_api_key),
):
    """
    向赛事书单批量添加参赛帖子。

    - **tournament_channel_id**: 赛事频道ID
    - **items**: 帖子列表，每项包含 thread_id（必填）、comment（可选）、display_order（可选）、tournament_participated_at（可选）
    """
    try:
        async with AsyncSessionFactory() as session:
            service = TournamentService(
                session, redis_client=getattr(cache_service_instance, "_redis", None)
            )
            added = await service.add_items(tournament_channel_id, request.items)

        return {
            "message": f"成功添加 {len(added)} 个参赛帖子",
            "added_count": len(added),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加赛事帖子失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加赛事帖子失败: {e}",
        )


@router.delete(
    "/{tournament_channel_id}/items/delete",
    summary="从赛事移除参赛帖子",
)
async def remove_tournament_items(
    tournament_channel_id: int,
    request: BooklistItemsDeleteRequest,
    api_key: bool = Depends(require_api_key),
):
    """
    从赛事书单批量移除参赛帖子。

    - **tournament_channel_id**: 赛事频道ID
    - **thread_ids**: 要移除的帖子ID列表
    """
    try:
        thread_ids = [int(tid) for tid in request.thread_ids]
        async with AsyncSessionFactory() as session:
            service = TournamentService(
                session, redis_client=getattr(cache_service_instance, "_redis", None)
            )
            deleted_count = await service.remove_items(
                tournament_channel_id, thread_ids
            )

        return {
            "message": f"成功从赛事移除 {deleted_count} 个帖子",
            "deleted_count": deleted_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除赛事帖子失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除赛事帖子失败",
        )


@router.delete("/{tournament_channel_id}", summary="删除赛事书单")
async def delete_tournament(
    tournament_channel_id: int,
    api_key: bool = Depends(require_api_key),
):
    """
    删除整个赛事书单及其所有关联帖子。

    - **tournament_channel_id**: 赛事频道ID
    """
    try:
        async with AsyncSessionFactory() as session:
            service = TournamentService(
                session, redis_client=getattr(cache_service_instance, "_redis", None)
            )
            success = await service.delete_tournament(tournament_channel_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="赛事书单不存在",
            )

        return {"message": "赛事书单删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除赛事书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除赛事书单失败",
        )


@router.patch("/{tournament_channel_id}", summary="更新赛事书单详情")
async def update_tournament(
    tournament_channel_id: int,
    request: TournamentUpdateRequest,
    api_key: bool = Depends(require_api_key),
):
    """
    更新赛事书单的标题、描述、封面图、可见性等元信息。

    - **tournament_channel_id**: 赛事频道ID
    - 请求体中的字段均为可选，仅更新传入的字段
    """
    try:
        async with AsyncSessionFactory() as session:
            service = TournamentService(
                session, redis_client=getattr(cache_service_instance, "_redis", None)
            )
            booklist = await service.update_tournament(tournament_channel_id, request)

            return {
                "message": "赛事书单已更新",
                "booklist_id": booklist.id,  # type: ignore[arg-type]
                "title": booklist.title,
                "description": booklist.description,
                "cover_image_url": booklist.cover_image_url,
                "is_public": booklist.is_public,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新赛事书单失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新赛事书单失败",
        )


@router.patch(
    "/{tournament_channel_id}/items/{thread_id}",
    summary="更新参赛帖子信息",
)
async def update_tournament_item(
    tournament_channel_id: int,
    thread_id: int,
    update_data: TournamentItemUpdateRequest,
    api_key: bool = Depends(require_api_key),
):
    """
    更新赛事书单中某个帖子的信息。

    - **tournament_channel_id**: 赛事频道ID
    - **thread_id**: 帖子ID
    - **update_data**: 要更新的字段（comment, display_order, tournament_participated_at）
    """
    try:
        async with AsyncSessionFactory() as session:
            service = TournamentService(
                session, redis_client=getattr(cache_service_instance, "_redis", None)
            )
            updated = await service.update_item(
                tournament_channel_id, thread_id, update_data
            )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定的帖子不在该赛事中",
            )

        return {"message": "赛事项更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新赛事项失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新赛事项失败",
        )
