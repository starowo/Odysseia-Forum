"""关注列表相关路由"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from api.v1.dependencies.security import get_current_user
from api.v1.schemas.follows import FollowedThreadResponse, FollowsListResponse
from api.v1.schemas.search import AuthorDetail
from api.v1.utils import ThreadDetailBuilder
from shared.database import AsyncSessionFactory
from shared.channel_mapping_utils import ChannelMappingUtils
from core.cache_service import CacheService
from core.follow_repository import ThreadFollowRepository
from core.notification_repository import NotificationRepository
from core.thread_presentation_service import ThreadPresentationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/follows", tags=["关注列表"])

# 全局变量，将在应用启动时由 api_main.py 注入
channel_mappings_config: Dict[int, List[Dict]] = {}
cache_service_instance: Optional[CacheService] = None


@router.get("/", summary="获取用户的关注列表", response_model=FollowsListResponse)
async def get_follows(
    limit: int = 10000,
    offset: int = 0,
    active_flag: Optional[bool] = Query(
        default=None, description="True=当前关注，False=过去关注，不传=全部"
    ),
    channel_ids: Optional[List[Union[int, str]]] = Query(
        default=None, description="频道ID列表（可选，用于按频道筛选）"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    获取当前用户关注的帖子列表

    - **limit**: 返回数量限制（默认10000）
    - **offset**: 偏移量（默认0）
    - **active_flag**: 筛选关注状态（True=当前关注，False=过去关注，不传=全部）
    - **channel_ids**: 频道ID列表（可选，用于按频道筛选）

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
    if not current_user:
        return {"total": 0, "threads": [], "limit": limit, "offset": offset}

    try:
        user_id = int(current_user["id"])

        # 将前端可能传入的字符串雪花 ID 统一转为 int
        effective_channel_ids: Optional[List[int]] = None
        if channel_ids:
            try:
                effective_channel_ids = [int(cid) for cid in channel_ids]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的频道ID格式",
                )

            # 通过频道映射解析，将父频道展开为实际子频道 ID 列表
            if cache_service_instance:
                all_indexed_channels = (
                    cache_service_instance.get_indexed_channel_ids_list()
                )
                channel_result = ChannelMappingUtils(channel_mappings_config).resolve(
                    channel_ids=effective_channel_ids,
                    include_tags=[],
                    exclude_tags=[],
                    tag_logic="or",
                    all_indexed_channels=all_indexed_channels,
                )
                effective_channel_ids = channel_result.effective_channel_ids

        async with AsyncSessionFactory() as session:
            follow_service = ThreadFollowRepository(session)
            records, total = await follow_service.get_user_follows(
                user_id=user_id,
                limit=limit,
                offset=offset,
                active_flag=active_flag,
                channel_ids=effective_channel_ids,
            )
            thread_dtos = [record.thread for record in records]
            presentation_context = await ThreadPresentationService(session).load(
                user_id, thread_dtos
            )
            builder = ThreadDetailBuilder(channel_mappings_config)
            threads: list[FollowedThreadResponse] = []
            for record in records:
                detail = builder.build(
                    record.thread,
                    set(),
                    presentation_context=presentation_context,
                )
                response_data = detail.model_dump()
                response_data["author"] = (
                    AuthorDetail.model_validate(record.author)
                    if record.author
                    else None
                )
                threads.append(
                    FollowedThreadResponse(
                        **response_data,
                        latest_update_at=record.thread.latest_update_at,
                        latest_update_link=record.thread.latest_update_link,
                        followed_at=record.followed_at,
                        last_viewed_at=record.last_viewed_at,
                        has_update="unread"
                        in presentation_context.viewer_flags.for_thread(
                            record.thread.thread_id
                        ),
                        active_flag=record.active_flag,
                    )
                )

        return {"total": total, "threads": threads, "limit": limit, "offset": offset}

    except HTTPException:
        raise
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
            marked_read = await NotificationRepository(session).mark_all_read(user_id)
            await session.commit()

        return {"message": "已标记所有动态为已查看", "marked_read": marked_read}

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
    if not current_user:
        return {"unread_count": 0}

    try:
        user_id = int(current_user["id"])

        async with AsyncSessionFactory() as session:
            count = await NotificationRepository(session).unread_count(user_id=user_id)

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
            follow_service = ThreadFollowRepository(session)
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

            follow_service = ThreadFollowRepository(session)
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
