"""
偏好仓库集成测试（PostgreSQL 后端）。

覆盖 preferences.py API 背后的 PreferencesRepository 层：
- get_user_preferences（获取或 None）
- save_user_preferences（创建 + 更新）
- guild 作用域隔离

PG 关注点：JSON 列的序列化/反序列化
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from core.preferences_repository import PreferencesRepository


@pytest_asyncio.fixture(scope="function")
async def pref_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供已清理的独立会话。"""
    async with db_session_factory() as session:
        yield session


@pytest.mark.asyncio
class TestGetPreferences:
    """获取偏好设置"""

    async def test_get_nonexistent_returns_none(self, pref_session: AsyncSession):
        """无偏好的用户 → None"""
        repo = PreferencesRepository(pref_session)
        result = await repo.get_user_preferences(user_id=1)
        assert result is None

    async def test_get_default_guild_zero(self, pref_session: AsyncSession):
        """未指定 guild_id → 默认 guild_id=0"""
        repo = PreferencesRepository(pref_session)
        await repo.save_user_preferences(
            user_id=1,
            prefs_data={"include_keywords": "test"},
        )
        result = await repo.get_user_preferences(user_id=1)
        assert result is not None
        assert result.include_keywords == "test"

    async def test_get_with_explicit_guild(self, pref_session: AsyncSession):
        """指定 guild_id → 正确隔离"""
        repo = PreferencesRepository(pref_session)
        await repo.save_user_preferences(
            user_id=1,
            guild_id=5,
            prefs_data={"include_keywords": "guild5"},
        )
        # 相同 user_id 不同 guild → 隔离
        result0 = await repo.get_user_preferences(user_id=1, guild_id=0)
        assert result0 is None
        result5 = await repo.get_user_preferences(user_id=1, guild_id=5)
        assert result5 is not None
        assert result5.include_keywords == "guild5"


@pytest.mark.asyncio
class TestSavePreferences:
    """保存偏好设置"""

    async def test_save_creates_new(self, pref_session: AsyncSession):
        """新用户 → 创建偏好记录"""
        repo = PreferencesRepository(pref_session)
        result = await repo.save_user_preferences(
            user_id=1,
            prefs_data={
                "include_keywords": "百合",
                "sort_method": "reaction_count",
                "results_per_page": 10,
            },
        )
        assert result.user_id == 1
        assert result.include_keywords == "百合"
        assert result.sort_method == "reaction_count"
        assert result.results_per_page == 10

    async def test_save_updates_existing(self, pref_session: AsyncSession):
        """已有偏好 → 更新覆盖"""
        repo = PreferencesRepository(pref_session)
        await repo.save_user_preferences(
            user_id=1,
            prefs_data={"include_keywords": "old", "sort_method": "created_at"},
        )
        result = await repo.save_user_preferences(
            user_id=1,
            prefs_data={"include_keywords": "new"},
        )
        assert result.include_keywords == "new"
        # 未在更新中指定的字段保持旧值
        assert result.sort_method == "created_at"

    async def test_save_json_columns(self, pref_session: AsyncSession):
        """JSON 列的正确序列化/反序列化"""
        repo = PreferencesRepository(pref_session)
        result = await repo.save_user_preferences(
            user_id=1,
            prefs_data={
                "include_tags": ["百合", "纯爱"],
                "exclude_tags": ["后宫"],
                "preferred_channels": [100, 200],
                "include_authors": [1, 2, 3],
            },
        )
        assert result.include_tags == ["百合", "纯爱"]
        assert result.exclude_tags == ["后宫"]
        assert result.preferred_channels == [100, 200]
        assert result.include_authors == [1, 2, 3]

    async def test_save_exemption_markers_default(self, pref_session: AsyncSession):
        """豁免标记默认值 ['禁', '🈲']"""
        repo = PreferencesRepository(pref_session)
        result = await repo.save_user_preferences(
            user_id=1,
            prefs_data={"include_keywords": "test"},
        )
        assert result.exclude_keyword_exemption_markers == ["禁", "🈲"]

    async def test_save_partial_update_preserves_others(
        self, pref_session: AsyncSession
    ):
        """部分更新不会清除其他字段"""
        repo = PreferencesRepository(pref_session)
        await repo.save_user_preferences(
            user_id=1,
            prefs_data={
                "include_keywords": "full",
                "sort_method": "comprehensive",
                "results_per_page": 20,
                "preview_image_mode": "full_width",
            },
        )
        # 只更新一个字段
        updated = await repo.save_user_preferences(
            user_id=1,
            prefs_data={"results_per_page": 50},
        )
        assert updated.results_per_page == 50
        assert updated.include_keywords == "full"
        assert updated.sort_method == "comprehensive"
        assert updated.preview_image_mode == "full_width"


@pytest.mark.asyncio
class TestGuildIsolation:
    """跨 guild 偏好隔离"""

    async def test_same_user_different_guilds(self, pref_session: AsyncSession):
        """同一用户不同 guild → 独立偏好"""
        repo = PreferencesRepository(pref_session)

        await repo.save_user_preferences(
            user_id=1,
            guild_id=10,
            prefs_data={"sort_method": "reaction_count"},
        )
        await repo.save_user_preferences(
            user_id=1,
            guild_id=20,
            prefs_data={"sort_method": "created_at"},
        )

        g10 = await repo.get_user_preferences(user_id=1, guild_id=10)
        g20 = await repo.get_user_preferences(user_id=1, guild_id=20)

        assert g10 is not None
        assert g20 is not None
        assert g10.sort_method == "reaction_count"
        assert g20.sort_method == "created_at"

    async def test_different_users_same_guild(self, pref_session: AsyncSession):
        """不同用户同一 guild → 独立偏好"""
        repo = PreferencesRepository(pref_session)

        await repo.save_user_preferences(
            user_id=1,
            guild_id=0,
            prefs_data={"include_keywords": "user1"},
        )
        await repo.save_user_preferences(
            user_id=2,
            guild_id=0,
            prefs_data={"include_keywords": "user2"},
        )

        u1 = await repo.get_user_preferences(user_id=1)
        u2 = await repo.get_user_preferences(user_id=2)

        assert u1 is not None
        assert u2 is not None
        assert u1.include_keywords == "user1"
        assert u2.include_keywords == "user2"
