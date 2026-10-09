"""Banner API 范围选择和关键词反选回归测试。"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from api.v1.routers import banner as router
from banner.banner_service import BannerService
from core.banner_carousel_repository import BannerCarouselRepository
from core.banner_title_filter_repository import BannerTitleFilterRepository
from dto.preferences import UserSearchPreferencesDTO
from models import BannerCarousel
from models.channel import Channel
from models.banner_waitlist import BannerWaitlist
from conftest import TEST_DATABASE_URL


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requested, legacy, preferred, failure, expected, all_channels",
    [
        ([20, 10, 20], 30, [40], False, [20, 10, 30], False),
        (None, None, [20, 10, 20], False, [20, 10], False),
        (None, None, [], False, [], True),
        (None, None, None, False, [], True),
        (None, None, [20], True, [], True),
        ([10], None, [20], True, [10], False),
    ],
)
async def test_api_channel_precedence(
    monkeypatch, requested, legacy, preferred, failure, expected, all_channels
):
    """显式范围优先于偏好，空偏好及读取失败时回退全部。"""
    # 候选为空以隔离范围选择，并验证偏好仅加载一次。
    factory = MagicMock()
    monkeypatch.setattr(router, "async_session_factory", factory)
    monkeypatch.setattr(router.RedisManager, "get_client", MagicMock())
    preferences = AsyncMock(
        return_value=UserSearchPreferencesDTO(
            user_id=42,
            preferred_channels=preferred,
        )
    )
    if failure:
        preferences.side_effect = RuntimeError("unavailable")
    monkeypatch.setattr(router, "get_user_preferences_cached", preferences)
    fetch = AsyncMock(return_value=[])
    monkeypatch.setattr(BannerService, "get_active_banners", fetch)
    assert await router.get_active_banners(requested, legacy, {"id": "42"}) == []
    preferences.assert_awaited_once()
    fetch.assert_awaited_once_with(channel_ids=expected, all_channels=all_channels)


@pytest.mark.asyncio
async def test_all_channels_order_limits_and_expiry(monkeypatch):
    """所有范围批量读取、稳定排序且不改变旧调用的全局默认值。"""
    now = datetime(2026, 9, 15, 12)
    monkeypatch.setattr("core.banner_carousel_repository.utc_now", lambda: now)
    engine = create_engine("sqlite://")
    BannerCarousel.__table__.create(engine)
    try:
        with Session(engine) as session:
            scope_offsets = {20: 1, 10: 2, None: 3}
            for cid in [20, 10, None]:
                for i in range(7):
                    session.add(
                        BannerCarousel(
                            id=i * 3 + scope_offsets[cid],
                            thread_id=(cid or 30) * 100 + i,
                            channel_id=cid,
                            title="标题",
                            position=i,
                            end_time=now + timedelta(hours=1),
                        )
                    )
            session.add(
                BannerCarousel(
                    thread_id=9999, channel_id=99, title="已到期", end_time=now
                )
            )
            session.commit()
            adapter = MagicMock()
            adapter.execute = AsyncMock(side_effect=session.execute)
            service = BannerService(adapter)
            result = await service.get_active_banners(all_channels=True)
            assert [b.thread_id for b in result] == [
                2000,
                1000,
                3000,
                2001,
                1001,
                3001,
                2002,
                1002,
                3002,
                2003,
                1003,
                2004,
                1004,
            ]
            assert adapter.execute.await_count == 2
            result = await service.get_active_banners(channel_ids=[20, 10, 20])
            assert [b.thread_id for b in result] == [
                2000,
                1000,
                3000,
                2001,
                1001,
                3001,
                2002,
                1002,
                3002,
                2003,
                1003,
                2004,
                1004,
            ]
            assert len(await BannerCarouselRepository(adapter).get_active()) == 3
    finally:
        engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "keywords, markers, titles, excluded",
    [
        ("cat", [], {1: "CAT event", 2: "dog event", 3: "cats event"}, {1, 3}),
        ("cat，dog", [], {1: "cat event", 2: "dog event", 3: "bird"}, {1, 2}),
        ("cat", ["禁", "🈲"], {1: "cat 禁", 2: "cat 🈲", 3: "cat event"}, {3}),
        ("cat", ["safe"], {1: "cat safe", 2: "cat one two three four safe"}, {2}),
        ("cat", [], {1: "cat 禁", 2: "cat 🈲"}, {1, 2}),
        ("猫咪", [], {1: "猫咪 活动", 2: "狗狗 活动"}, {1}),
        ("", [], {1: "cat"}, set()),
        ("cat", [], {1: "", 2: '"quoted" cat $$'}, {2}),
    ],
)
async def test_channel_title_fts_in_postgres(keywords, markers, titles, excluded):
    """在 PostgreSQL 执行真实分词匹配，无需创建或修改任何表。"""
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with AsyncSession(engine) as session:
            assert (
                await BannerTitleFilterRepository(session).get_excluded_ids(
                    titles, keywords, markers
                )
                == excluded
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_api_filters_title_snapshots_without_waitlist_backfill(
    db_session_factory, monkeypatch
):
    """同目标的不同标题分别过滤，全局也过滤且不从等待队列补位。"""
    from shared.time_utils import utc_now

    now = utc_now()
    async with db_session_factory() as session:
        session.add(Channel(channel_id=900, guild_id=1, name="不用于过滤的频道名"))
        for scope, title in [(10, "cat event"), (20, "dog event"), (None, "cat event")]:
            session.add(
                BannerCarousel(
                    thread_id=900,
                    channel_id=scope,
                    title=title,
                    target_type=2,
                    cover_image_url="https://example.com/cover.png",
                    end_time=now + timedelta(days=1),
                )
            )
        session.add(
            BannerWaitlist(
                thread_id=900,
                channel_id=10,
                title="waiting dog event",
                target_type=2,
                cover_image_url="https://example.com/waiting.png",
            )
        )
        await session.commit()
    monkeypatch.setattr(router, "async_session_factory", db_session_factory)
    monkeypatch.setattr(
        router,
        "get_user_preferences_cached",
        AsyncMock(
            return_value=UserSearchPreferencesDTO(
                user_id=42,
                exclude_keywords="cat",
                exclude_keyword_exemption_markers=[],
                include_keywords="not-present",
                include_authors=[999],
                include_tags=["not-present"],
            )
        ),
    )
    result = await router.get_active_banners(None, None, {"id": "42"})
    assert [(item.channel_id, item.title) for item in result] == [(20, "dog event")]
    assert result[0].guild_id == 1
    assert result[0].cover_image_url == "https://example.com/cover.png"
    assert result[0].model_dump(mode="json")["thread_id"] == "900"
