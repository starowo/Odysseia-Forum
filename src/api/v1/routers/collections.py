"""收藏相关路由"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.dependencies.security import get_current_user
from booklist.booklist_service import BooklistService
from core.collection_service import CollectionService
from core.thread_service import ThreadService
from shared.database import AsyncSessionFactory
from shared.enum.collection_type import CollectionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collection", tags=["收藏"])


@router.post("/batch/add", summary="批量添加收藏")
async def batch_add_collections(
    target_ids: List[int],
    target_type: int = CollectionType.THREAD,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    批量添加收藏

    - target_ids: 目标ID列表（帖子ID或书单ID）
    - target_type: 目标类型，1=帖子，2=书单，默认为1（帖子）
    """
    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            collection_service = CollectionService(session)
            result = await collection_service.add_collections(
                user_id, target_type, target_ids
            )

            # 如果收藏的是帖子，则更新其收藏计数
            if target_type == CollectionType.THREAD.value and result.added_count > 0:
                thread_service = ThreadService(session)
                await thread_service.update_collection_counts(result.added_ids, 1)

            # 如果收藏的是书单，则更新其收藏计数
            if target_type == CollectionType.BOOKLIST.value and result.added_count > 0:
                booklist_service = BooklistService(session)
                await booklist_service.update_collection_counts(result.added_ids, 1)

        return {
            "message": "批量收藏操作完成",
            "user_id": user_id,
            "target_type": target_type,
            "added_count": result.added_count,
            "duplicate_count": result.duplicate_count,
            "added_ids": result.added_ids,
        }

    except Exception as e:
        logger.error(f"批量添加收藏失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="批量添加收藏失败"
        )


@router.post("/batch/remove", summary="批量移除收藏")
async def batch_remove_collections(
    target_ids: List[int],
    target_type: int = CollectionType.THREAD,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    批量移除收藏

    - target_ids: 目标ID列表（帖子ID或书单ID）
    - target_type: 目标类型，1=帖子，2=书单，默认为1（帖子）
    """
    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            collection_service = CollectionService(session)
            result = await collection_service.remove_collections(
                user_id, target_type, target_ids
            )

            # 如果移除的是帖子收藏，则更新其收藏计数
            if target_type == CollectionType.THREAD.value and result.removed_count > 0:
                thread_service = ThreadService(session)
                await thread_service.update_collection_counts(result.removed_ids, -1)

            # 如果移除的是书单收藏，则更新其收藏计数
            if (
                target_type == CollectionType.BOOKLIST.value
                and result.removed_count > 0
            ):
                booklist_service = BooklistService(session)
                await booklist_service.update_collection_counts(result.removed_ids, -1)

        return {
            "message": "批量取消收藏操作完成",
            "user_id": user_id,
            "target_type": target_type,
            "removed_count": result.removed_count,
            "not_found_count": result.not_found_count,
            "removed_ids": result.removed_ids,
        }

    except Exception as e:
        logger.error(f"批量移除收藏失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="批量移除收藏失败"
        )
