import logging

from sqlalchemy.ext.asyncio import async_sessionmaker
from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.dependencies.security import require_auth
from api.v1.schemas.preferences import (
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
)
from core.preferences_repository import PreferencesRepository
from shared.redis_client import RedisManager

logger = logging.getLogger(__name__)

# 全局变量，将在应用启动时由 bot_main.py 注入
async_session_factory: async_sessionmaker | None = None
main_guild_id: int = 0  # 注入的主服务器 ID

router = APIRouter(
    prefix="/preferences", tags=["用户偏好"], dependencies=[Depends(require_auth)]
)


@router.get(
    "/users/{user_id}",
    response_model=UserPreferencesResponse,
    summary="获取指定用户的搜索偏好",
)
async def get_user_preferences(user_id: int):
    """
    获取用户的搜索偏好设置。固定使用配置的主服务器 ID。
    """
    if not async_session_factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preferences 服务尚未初始化",
        )

    try:
        async with async_session_factory() as session:
            repo = PreferencesRepository(
                session, redis_client=RedisManager.get_client()
            )
            # 使用注入的 main_guild_id
            prefs_dto = await repo.get_user_preferences(user_id, main_guild_id)
            if not prefs_dto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"未找到用户ID {user_id} 的偏好设置",
                )
            return prefs_dto
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户偏好时发生内部错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户偏好时发生内部错误",
        )


@router.put(
    "/users/{user_id}",
    response_model=UserPreferencesResponse,
    summary="创建或更新用户搜索偏好",
)
async def update_user_preferences(user_id: int, request: UserPreferencesUpdateRequest):
    """
    创建或更新用户的搜索偏好设置。固定使用配置的主服务器 ID。
    """
    if not async_session_factory:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preferences 服务尚未初始化",
        )

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请求体不能为空"
        )

    try:
        async with async_session_factory() as session:
            repo = PreferencesRepository(
                session, redis_client=RedisManager.get_client()
            )
            # 使用注入的 main_guild_id
            updated_prefs = await repo.save_user_preferences(
                user_id, update_data, main_guild_id
            )
            return updated_prefs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户偏好时发生内部错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户偏好时发生内部错误",
        )
