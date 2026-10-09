import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from dto.preferences import UserSearchPreferencesDTO
from models import UserSearchPreferences
from shared.enum import CacheKeys, ConstantEnum

logger = logging.getLogger(__name__)


class PreferencesRepository:
    """封装与用户偏好设置相关的数据库操作。"""

    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self._redis = redis_client

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

        # 写入成功后刷新 Redis 缓存
        if self._redis:
            try:
                cache_key = CacheKeys.USER_PREFERENCES.format(
                    user_id=user_id, guild_id=guild_id
                )
                result_dto = UserSearchPreferencesDTO.model_validate(prefs)
                await self._redis.setex(
                    cache_key,
                    int(ConstantEnum.PREF_CACHE_TTL),
                    json.dumps(result_dto.model_dump(), default=str),
                )
            except Exception:
                pass  # Redis 故障不影响主流程

        return UserSearchPreferencesDTO.model_validate(prefs)
