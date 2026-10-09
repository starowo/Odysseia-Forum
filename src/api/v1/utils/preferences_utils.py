"""用户搜索偏好缓存读取工具。"""

import json
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.preferences_repository import PreferencesRepository
from dto.preferences import UserSearchPreferencesDTO
from shared.enum import CacheKeys, ConstantEnum


async def get_user_preferences_cached(
    redis_client, session_factory: async_sessionmaker, user_id: int, guild_id: int
) -> Optional[UserSearchPreferencesDTO]:
    """从 Redis 缓存读取用户偏好，未命中则查 DB 并回填缓存。

    供 search 和 banner 路由共用。
    """
    cache_key = CacheKeys.USER_PREFERENCES.format(user_id=user_id, guild_id=guild_id)

    # 尝试 Redis 命中
    try:
        raw = await redis_client.get(cache_key)
        if raw:
            data = json.loads(raw)
            return UserSearchPreferencesDTO(**data)
    except Exception:
        pass  # Redis 异常时降级到 DB

    # 缓存未命中，查 DB
    async with session_factory() as session:
        pref_repo = PreferencesRepository(session)
        prefs = await pref_repo.get_user_preferences(user_id, guild_id)

    # 回填缓存
    if prefs:
        try:
            await redis_client.setex(
                cache_key,
                int(ConstantEnum.PREF_CACHE_TTL),
                json.dumps(prefs.model_dump(), default=str),
            )
        except Exception:
            pass

    return prefs
