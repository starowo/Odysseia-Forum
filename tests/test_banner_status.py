"""管理状态聚合和多消息输出回归测试。"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from banner.banner_service import BannerService
from banner.cog import BannerManagement
from banner.dto.banner_scope_status import BannerScopeStatus
from banner.dto.banner_status_item import BannerStatusItem
from banner.views.banner_status_view import BannerStatusView
from models import BannerCarousel, BannerWaitlist


@pytest.mark.asyncio
@pytest.mark.parametrize("configured_count", [1, 8])
async def test_status_uses_two_queries_and_detached_dtos(configured_count):
    """完整分组、等待数量及过期过滤不随配置频道数量增加查询。"""
    # 用真实 SQL 验证独立范围、超额记录和未配置频道。
    now = datetime(2026, 9, 15, 12)
    engine = create_engine("sqlite://")
    BannerCarousel.__table__.create(engine)
    BannerWaitlist.__table__.create(engine)
    try:
        with Session(engine) as session:
            for i in range(4):
                session.add(
                    BannerCarousel(
                        thread_id=100 + i,
                        title=f"全局{i}",
                        channel_id=None,
                        end_time=now + timedelta(days=1),
                        position=3 - i,
                    )
                )
            session.add_all(
                [
                    BannerCarousel(
                        thread_id=200,
                        title="频道目标",
                        channel_id=1,
                        target_type=2,
                        cover_image_url="https://example.com/a",
                        end_time=now + timedelta(hours=1),
                    ),
                    BannerCarousel(
                        thread_id=201, title="已到期", channel_id=1, end_time=now
                    ),
                    BannerCarousel(
                        thread_id=202,
                        title="未配置",
                        channel_id=99,
                        end_time=now + timedelta(hours=1),
                    ),
                    BannerCarousel(
                        thread_id=203,
                        title="仅过期",
                        channel_id=98,
                        end_time=now - timedelta(seconds=1),
                    ),
                ]
            )
            for cid in [None, None, 1, 88]:
                session.add(BannerWaitlist(thread_id=300, title="等待", channel_id=cid))
            session.commit()
            adapter = MagicMock()
            adapter.execute = AsyncMock(side_effect=session.execute)
            scopes = await BannerService(adapter).get_status(
                list(range(1, configured_count + 1)), now
            )
            assert adapter.execute.await_count == 2

        # 会话关闭后 DTO 仍可用于构建消息。
        assert [s.channel_id for s in scopes] == [
            None,
            *range(1, configured_count + 1),
            88,
            99,
        ]
        assert [i.target_id for i in scopes[0].items] == [103, 102, 101, 100]
        assert scopes[0].waiting_count == 2
        assert scopes[0].capacity == 3
        assert scopes[1].waiting_count == 1
        assert scopes[1].capacity == 3
        assert [i.target_id for i in scopes[1].items] == [200]
        assert scopes[-2].waiting_count == 1 and not scopes[-2].items
        assert scopes[-1].waiting_count == 0
        text = "\n".join(BannerStatusView.build_messages(scopes, {}, now))
        assert "全频道：轮播 4/3" in text
        assert "[频道] 频道目标" in text
        assert "已到期" not in text
    finally:
        engine.dispose()


def test_status_messages_keep_all_items_and_repeat_scope():
    """长结果按行拆分，不遗漏 ID，续条保留范围标题。"""
    now = datetime(2026, 9, 15, 12)
    scopes = [BannerScopeStatus(None, 3, 0, [])]
    for cid in range(1, 10):
        scopes.append(
            BannerScopeStatus(
                cid,
                3,
                cid,
                [
                    BannerStatusItem(
                        cid * 100 + i, 1, "长" * 31, now + timedelta(hours=8)
                    )
                    for i in range(20)
                ],
            )
        )
    messages = BannerStatusView.build_messages(scopes, {}, now)
    assert len(messages) > 1
    for message in messages:
        assert len(message) <= 1900
        assert "：轮播" in message.splitlines()[2]
    text = "\n".join(messages)
    for cid in range(1, 10):
        assert f"{cid}：轮播 20/3｜已审核待展示 {cid}" in text
        for i in range(20):
            assert text.count(f"ID：{cid * 100 + i}｜") == 1
    assert "长" * 30 + "..." in text
    assert "长" * 31 not in text
    assert "暂无轮播" in text


@pytest.mark.asyncio
async def test_command_resolves_extra_names_and_sends_private_messages(monkeypatch):
    """配置名称优先，补充频道使用缓存名称或 ID，所有分条消息保持私密。"""
    now = datetime(2026, 9, 15, 12)
    monkeypatch.setattr("banner.cog.utc_now", lambda: now)
    scopes = [BannerScopeStatus(None, 3, 0, [])] + [
        BannerScopeStatus(
            cid,
            3,
            1,
            [
                BannerStatusItem(cid * 100 + i, 2, "短标题", now + timedelta(hours=1))
                for i in range(25)
            ],
        )
        for cid in [1, 88, 99]
    ]
    get_status = AsyncMock(return_value=scopes)
    monkeypatch.setattr(BannerService, "get_status", get_status)
    bot = MagicMock()
    bot.config = {"banner": {"enabled": False, "available_channels": {"1": "配置频道"}}}
    cached_channel = MagicMock()
    cached_channel.name = "缓存频道"
    bot.get_channel.side_effect = lambda cid: cached_channel if cid == 88 else None
    management = BannerManagement(bot, MagicMock())
    interaction = MagicMock()
    interaction.followup.send = AsyncMock()
    await BannerManagement.view_status.callback(management, interaction)
    get_status.assert_awaited_once_with([1], now)
    calls = interaction.followup.send.await_args_list
    assert len(calls) > 1
    text = "\n".join(call.args[0] for call in calls)
    for name in ["配置频道", "缓存频道", "99"]:
        assert f"{name}：轮播" in text
    assert "短标题..." not in text
    assert "[频道] 短标题" in text
    assert all(call.kwargs["ephemeral"] for call in calls)
