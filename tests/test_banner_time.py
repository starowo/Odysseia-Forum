"""Banner 状态展示和轮播到期边界的 UTC 回归测试。"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from banner.banner_service import BannerService
from banner.cog import BannerManagement
from banner.dto.banner_scope_status import BannerScopeStatus
from banner.dto.banner_status_item import BannerStatusItem
from core.banner_carousel_repository import BannerCarouselRepository
from models import BannerCarousel


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hours, remaining",
    [
        (None, None),
        (49, "剩余 2 天"),
        (24, "剩余 1 天"),
        (23 + 59 / 60, "剩余 23 小时"),
        (1, "剩余 1 小时"),
        (0.5, "剩余不足1小时"),
    ],
)
async def test_view_status_with_naive_utc(monkeypatch, hours, remaining):
    """数据库返回无时区时间时，状态展示正常且正确显示天数或小时数。"""
    # 固定 UTC 时间并模拟数据库返回的轮播数据。
    now = datetime(2026, 9, 15, 12)
    monkeypatch.setattr("banner.cog.utc_now", lambda: now)
    banners = (
        []
        if hours is None
        else [
            BannerStatusItem(
                target_id=123,
                target_type=1,
                title="赛事",
                end_time=now + timedelta(hours=hours),
            )
        ]
    )
    monkeypatch.setattr(
        BannerService,
        "get_status",
        AsyncMock(return_value=[BannerScopeStatus(None, 3, 0, banners)]),
    )
    bot = MagicMock()
    bot.config = {"banner": {"enabled": False}}
    management = BannerManagement(bot, MagicMock())
    interaction = MagicMock()
    interaction.response.is_done.return_value = False
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    # 直接调用命令回调，避免启动后台清理任务。
    await BannerManagement.view_status.callback(management, interaction)

    interaction.followup.send.assert_awaited_once()
    message = interaction.followup.send.call_args.args[0]
    assert "Banner系统状态" in message
    assert f"全频道：轮播 {len(banners)}/3｜已审核待展示 0" in message
    assert interaction.followup.send.call_args.kwargs["ephemeral"] is True
    if remaining is not None:
        assert remaining in message


@pytest.mark.asyncio
@pytest.mark.parametrize("channel_id", [None, 456])
async def test_carousel_utc_duration_and_expiry(monkeypatch, channel_id):
    """在实际 SQL 查询中验证三天期限、秒级精度和到期边界。"""
    # 内存数据库只建轮播表，通过异步适配调用真实仓储 SQL。
    now = datetime(2026, 9, 15, 12, 0, 0, 123456)
    monkeypatch.setattr("core.banner_carousel_repository.utc_now", lambda: now)
    engine = create_engine("sqlite://")
    BannerCarousel.__table__.create(engine)
    try:
        with Session(engine) as session:
            async_session = MagicMock()
            async_session.execute = AsyncMock(side_effect=session.execute)
            async_session.add.side_effect = session.add
            repository = BannerCarouselRepository(async_session)
            await repository.add(123, channel_id, None, "赛事", 3)
            session.commit()
            banner = session.query(BannerCarousel).one()
            assert banner.start_time == now.replace(microsecond=0)
            assert banner.end_time == banner.start_time + timedelta(days=3)
            assert banner.end_time.tzinfo is None

            # 到期前仍有效，到期时从有效列表消失并进入过期列表。
            end_time = banner.end_time
            for offset, active in [(-1, True), (0, False), (1, False)]:
                now = end_time + timedelta(seconds=offset)
                channel_ids = [channel_id] if channel_id is not None else None
                assert await repository.get_active(channel_ids) == (
                    [banner] if active else []
                )
                assert await repository.get_count(channel_id) == int(active)
                assert await repository.get_expired() == ([] if active else [banner])
    finally:
        engine.dispose()
