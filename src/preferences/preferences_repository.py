import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.tag_cache_service import TagCacheService
from models import UserSearchPreferences
from search.dto.user_search_preferences import UserSearchPreferencesDTO

logger = logging.getLogger(__name__)


class PreferencesRepository:
    """封装与用户偏好设置相关的数据库操作。"""

    def __init__(self, session: AsyncSession, tag_service: TagCacheService):
        self.session = session
        self.tag_service = tag_service

    async def get_user_preferences(
        self, user_id: int
    ) -> Optional[UserSearchPreferencesDTO]:
        """获取用户的搜索偏好设置"""
        prefs_orm = await self.session.get(UserSearchPreferences, user_id)
        if not prefs_orm:
            return None
        return UserSearchPreferencesDTO.model_validate(prefs_orm)

    async def save_user_preferences(
        self, user_id: int, prefs_data: dict
    ) -> UserSearchPreferencesDTO:
        """创建或更新用户的搜索偏好设置"""
        prefs = await self.session.get(UserSearchPreferences, user_id)
        if prefs:
            for key, value in prefs_data.items():
                setattr(prefs, key, value)
        else:
            prefs = UserSearchPreferences(user_id=user_id, **prefs_data)
        self.session.add(prefs)
        await self.session.commit()
        await self.session.refresh(prefs)
        return UserSearchPreferencesDTO.model_validate(prefs)
