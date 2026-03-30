import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

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
        self, user_id: int, guild_id: int = 0
    ) -> Optional[UserSearchPreferencesDTO]:
        """获取用户在指定服务器的搜索偏好设置"""
        stmt = select(UserSearchPreferences).where(
            UserSearchPreferences.user_id == user_id,
            UserSearchPreferences.guild_id == guild_id,
        )
        result = await self.session.execute(stmt)
        prefs_orm = result.scalars().first()
        if not prefs_orm:
            return None
        return UserSearchPreferencesDTO.model_validate(prefs_orm)

    async def save_user_preferences(
        self, user_id: int, prefs_data: dict, guild_id: int = 0
    ) -> UserSearchPreferencesDTO:
        """创建或更新用户在指定服务器的搜索偏好设置"""
        stmt = select(UserSearchPreferences).where(
            UserSearchPreferences.user_id == user_id,
            UserSearchPreferences.guild_id == guild_id,
        )
        result = await self.session.execute(stmt)
        prefs = result.scalars().first()
        if prefs:
            for key, value in prefs_data.items():
                setattr(prefs, key, value)
        else:
            prefs = UserSearchPreferences(
                user_id=user_id, guild_id=guild_id, **prefs_data
            )
        self.session.add(prefs)
        await self.session.commit()
        await self.session.refresh(prefs)
        return UserSearchPreferencesDTO.model_validate(prefs)
