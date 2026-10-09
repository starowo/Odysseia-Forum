"""BOT 申请入口的按需频道索引回归测试。"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from banner.channel_sync import ChannelSyncService
from banner.listeners.banner_event_listener import BannerEventListener
from core.banner_application_repository import BannerApplicationRepository
from core.thread_repository import ThreadRepository
from models.banner_application import BannerApplication
from models.channel import Channel
from shared.enum import TargetType


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["form", "apply"])
@pytest.mark.parametrize("accessible", [True, False])
async def test_unindexed_channel_application(monkeypatch, entry, accessible):
    """两个 BOT 入口均能索引新频道，获取失败时不创建申请。"""
    # 模拟本地尚无帖子和频道，保留真实 BannerService 验证逻辑。
    monkeypatch.setenv("BOT_TOKEN", " test-bot-token ")
    session = AsyncMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = None
    session.execute.return_value = query_result
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session
    monkeypatch.setattr(
        ThreadRepository, "get_thread_with_tags", AsyncMock(return_value=None)
    )
    channel = Channel(channel_id=123, guild_id=456, name="赛事频道")
    sync = AsyncMock(return_value=channel if accessible else None)
    monkeypatch.setattr(ChannelSyncService, "fetch_and_index", sync)
    application = BannerApplication(
        id=1,
        thread_id=123,
        channel_id=123,
        applicant_id=789,
        cover_image_url="https://example.com/cover.png",
        target_scope="global",
        target_type=TargetType.CHANNEL.value,
    )
    create = AsyncMock(return_value=application)
    monkeypatch.setattr(BannerApplicationRepository, "create", create)
    monkeypatch.setattr(
        BannerApplicationRepository,
        "get_history_by_thread_id",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        BannerApplicationRepository,
        "update_review_message_info",
        AsyncMock(return_value=True),
    )
    bot = MagicMock()
    review_channel = MagicMock(spec=discord.Thread)
    review_channel.send = AsyncMock(return_value=MagicMock(id=999))
    bot.fetch_channel = AsyncMock(return_value=review_channel)
    listener = BannerEventListener(bot, session_factory, {"review_thread_id": 888})
    assert listener.channel_sync.bot_token == "test-bot-token"
    interaction = MagicMock()
    interaction.user.id = 789
    interaction.followup.send = AsyncMock()

    # 从真实事件入口执行，以捕获遗漏服务注入的回归。
    if entry == "form":
        await listener.on_banner_form_submit(
            interaction, 123, "https://example.com/cover.png", 456
        )
    else:
        await listener.on_banner_apply(
            interaction, 123, "https://example.com/cover.png", "global", 789, 123, 456
        )

    sync.assert_awaited_once_with(session, 123)
    if not accessible:
        create.assert_not_awaited()
        assert "未被索引" in interaction.followup.send.call_args.args[0]
    elif entry == "form":
        view = interaction.followup.send.call_args.kwargs["view"]
        assert view._thread_id == 123
        assert view._channel_id == 123
        assert view._guild_id == 456
    else:
        create.assert_awaited_once_with(
            thread_id=123,
            channel_id=123,
            applicant_id=789,
            cover_image_url="https://example.com/cover.png",
            target_scope="global",
            target_type=TargetType.CHANNEL.value,
        )
        review_channel.send.assert_awaited_once()
        assert "申请已提交" in interaction.followup.send.call_args.args[0]
