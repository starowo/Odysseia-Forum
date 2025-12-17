from fastapi import APIRouter, Depends, HTTPException, status

from api.v1.dependencies.security import require_auth
from api.v1.schemas.preferences import (
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
)
from preferences.cog import Preferences
from preferences.preferences_service import PreferencesService

# 全局变量，将在应用启动时由 bot_main.py 注入
preferences_cog_instance: Preferences | None = None

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
    根据 Discord 用户 ID，获取该用户的完整搜索偏好设置。

    - user_id: Discord 用户 ID
    - return: 用户的完整搜索偏好设置
    """
    if not preferences_cog_instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preferences 服务尚未初始化",
        )

    service: PreferencesService = preferences_cog_instance.preferences_service
    prefs_dto = await service.get_user_preferences(user_id)

    if not prefs_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到用户ID {user_id} 的偏好设置",
        )

    return prefs_dto


@router.put(
    "/users/{user_id}",
    response_model=UserPreferencesResponse,
    summary="创建或更新用户搜索偏好",
)
async def update_user_preferences(user_id: int, request: UserPreferencesUpdateRequest):
    """
    根据 Discord 用户 ID，创建或更新该用户的搜索偏好设置。

    - user_id: Discord 用户 ID
    - request: 要更新的偏好设置数据
    - return: 更新后的完整搜索偏好设置
    """
    if not preferences_cog_instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Preferences 服务尚未初始化",
        )

    service: PreferencesService = preferences_cog_instance.preferences_service
    update_data = request.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请求体不能为空"
        )

    updated_prefs = await service.save_user_preferences(user_id, update_data)
    return updated_prefs
