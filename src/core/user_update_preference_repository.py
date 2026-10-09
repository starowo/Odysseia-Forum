"""用户更新检测偏好仓库。"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models import UserUpdatePreference


class UserUpdatePreferenceRepository:
    """管理用户更新检测偏好的单表数据库操作。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_preference(
        self, user_id: int, thread_id: int
    ) -> Optional[UserUpdatePreference]:
        """获取用户在指定帖子上的更新检测偏好。"""
        # 查询用户在指定帖子上的偏好记录。
        stmt = select(UserUpdatePreference).where(
            UserUpdatePreference.user_id == user_id,
            UserUpdatePreference.thread_id == thread_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def set_auto_sync(self, user_id: int, thread_id: int, enabled: bool) -> None:
        """设置用户在指定帖子上的自动同步偏好。"""
        # 创建或更新自动同步偏好。
        preference = await self.get_preference(user_id, thread_id)
        if preference:
            preference.auto_sync = enabled
            if enabled:
                preference.no_remind = False
        else:
            preference = UserUpdatePreference(
                user_id=user_id, thread_id=thread_id, auto_sync=enabled
            )
            self.session.add(preference)
        await self.session.commit()

    async def set_no_remind(self, user_id: int, thread_id: int, enabled: bool) -> None:
        """设置用户在指定帖子上是否不再提醒。"""
        # 创建或更新不再提醒偏好。
        preference = await self.get_preference(user_id, thread_id)
        if preference:
            preference.no_remind = enabled
            if enabled:
                preference.auto_sync = False
        else:
            preference = UserUpdatePreference(
                user_id=user_id, thread_id=thread_id, no_remind=enabled
            )
            self.session.add(preference)
        await self.session.commit()

    async def get_user_preferences(self, user_id: int) -> list[UserUpdatePreference]:
        """获取用户的全部更新检测偏好。"""
        # 查询用户在所有帖子上的偏好记录。
        stmt = select(UserUpdatePreference).where(
            UserUpdatePreference.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reset_preference(self, user_id: int, thread_id: int) -> bool:
        """将指定帖子的更新检测偏好恢复为默认值。"""
        # 重置已有偏好，缺失记录时无需写入。
        preference = await self.get_preference(user_id, thread_id)
        if preference:
            preference.auto_sync = False
            preference.no_remind = False
            await self.session.commit()
            return True
        return False
