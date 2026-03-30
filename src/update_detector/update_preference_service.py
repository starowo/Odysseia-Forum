import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models.user_update_preference import UserUpdatePreference

logger = logging.getLogger(__name__)


class UpdatePreferenceService:
    """管理用户更新检测偏好的数据库操作"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_preference(
        self, user_id: int, thread_id: int
    ) -> Optional[UserUpdatePreference]:
        stmt = select(UserUpdatePreference).where(
            UserUpdatePreference.user_id == user_id,
            UserUpdatePreference.thread_id == thread_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def set_auto_sync(self, user_id: int, thread_id: int, enabled: bool) -> None:
        pref = await self.get_preference(user_id, thread_id)
        if pref:
            pref.auto_sync = enabled
        else:
            pref = UserUpdatePreference(
                user_id=user_id, thread_id=thread_id, auto_sync=enabled
            )
            self.session.add(pref)
        await self.session.commit()

    async def set_no_remind(self, user_id: int, thread_id: int, enabled: bool) -> None:
        pref = await self.get_preference(user_id, thread_id)
        if pref:
            pref.no_remind = enabled
        else:
            pref = UserUpdatePreference(
                user_id=user_id, thread_id=thread_id, no_remind=enabled
            )
            self.session.add(pref)
        await self.session.commit()

    async def get_user_preferences(
        self, user_id: int
    ) -> list[UserUpdatePreference]:
        """获取用户在所有帖子上的偏好设置"""
        stmt = select(UserUpdatePreference).where(
            UserUpdatePreference.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reset_preference(self, user_id: int, thread_id: int) -> bool:
        """重置用户在指定帖子上的偏好（恢复默认提醒行为）"""
        pref = await self.get_preference(user_id, thread_id)
        if pref:
            pref.auto_sync = False
            pref.no_remind = False
            await self.session.commit()
            return True
        return False
