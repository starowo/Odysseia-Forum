"""关注列表相关路由"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.dependencies.security import get_current_user
from shared.database import AsyncSessionFactory
from ThreadManager.services.follow_service import FollowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/follows", tags=["关注列表"])


@router.get("/", summary="获取用户的关注列表")
async def get_follows(
    limit: int = 10000,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    获取当前用户关注的帖子列表

    - **limit**: 返回数量限制（默认10000）
    - **offset**: 偏移量（默认0）

    返回格式：
    ```json
    {
        "total": 总数,
        "threads": [帖子列表],
        "limit": 限制数量,
        "offset": 偏移量
    }
    ```
    """
    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            follow_service = FollowService(session)
            threads, total = await follow_service.get_user_follows(
                user_id=user_id, limit=limit, offset=offset
            )

        return {"total": total, "threads": threads, "limit": limit, "offset": offset}

    except Exception as e:
        logger.error(f"获取关注列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取关注列表失败"
        )


@router.post("/mark-viewed", summary="标记关注列表已查看")
async def mark_all_viewed(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    标记用户的所有关注为已查看

    用于用户打开关注列表后，批量更新查看时间
    """
    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            follow_service = FollowService(session)
            success = await follow_service.update_last_viewed(
                user_id=user_id,
                thread_id=None,  # None表示更新所有关注
            )

        if success:
            return {"message": "已标记所有关注为已查看"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="标记失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记已查看失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="标记已查看失败"
        )


@router.get("/unread-count", summary="获取未读更新数量")
async def get_unread_count(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    获取用户未读更新的数量
    """
    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            follow_service = FollowService(session)
            count = await follow_service.get_unread_count(user_id=user_id)

        return {"unread_count": count}

    except Exception as e:
        logger.error(f"获取未读数量失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取未读数量失败"
        )


@router.post("/{thread_id}", summary="关注帖子")
async def add_follow(
    thread_id: int, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    添加关注

    - **thread_id**: 帖子Discord ID
    """
    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            follow_service = FollowService(session)
            success = await follow_service.add_follow(
                user_id=user_id,
                thread_id=thread_id,
                auto_view=True,  # 手动关注时标记为已查看
            )

        if success:
            return {"message": "关注成功", "thread_id": thread_id}
        else:
            return {"message": "已经关注过此帖", "thread_id": thread_id}

    except Exception as e:
        logger.error(f"添加关注失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="添加关注失败"
        )


@router.delete("/{thread_id}", summary="取消关注")
async def remove_follow(
    thread_id: int, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    取消关注

    - **thread_id**: 帖子Discord ID

    注意：用户不能取消关注自己的帖子
    """
    try:
        user_id = int(current_user["id"])

        # 检查是否是用户自己的帖子
        from sqlmodel import select

        from models import Thread

        async with AsyncSessionFactory() as session:
            # 查询帖子作者
            statement = select(Thread.author_id).where(Thread.thread_id == thread_id)
            result = await session.execute(statement)
            author_id = result.scalar_one_or_none()

            if author_id and author_id == user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="不能取消关注自己的帖子",
                )

            follow_service = FollowService(session)
            success = await follow_service.remove_follow(
                user_id=user_id, thread_id=thread_id
            )

        if success:
            return {"message": "已取消关注", "thread_id": thread_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="未关注此帖"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消关注失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="取消关注失败"
        )
