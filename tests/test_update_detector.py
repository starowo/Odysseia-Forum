"""更新检测试监听、DeepSeek 调用与 Redis 统计测试。"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import discord

from dto.update_detector import TokenEstimate, UpdateDetectionResult
from models import Thread as ThreadModel
from update_detector.cog import UpdateDetector
from update_detector.deepseek_service import DeepSeekService
from update_detector.prompt_builder import build_update_detection_prompt
from update_detector.token_estimator import TokenEstimator
from update_detector.token_stats_service import TokenStatsService
from update_detector.update_detector_views import UpdateDetectorView, build_update_embed


def test_token_estimator_counts_complete_prompt_and_attachment_names():
    """估算同时覆盖系统提示词、正文和附件名，并按请求向上取整。"""
    system_content, user_content = build_update_detection_prompt(
        thread_title="测试作品",
        first_message_content="作品简介",
        message_content="版本 v2 已更新",
        attachment_filenames=["settings.json"],
    )

    estimate = TokenEstimator().estimate(system_content, user_content, 2048)
    complete_content = system_content + user_content
    expected_ascii = sum(character.isascii() for character in complete_content)
    expected_non_ascii = len(complete_content) - expected_ascii

    assert estimate.ascii_character_count == expected_ascii
    assert estimate.non_ascii_character_count == expected_non_ascii
    assert estimate.chat_overhead_tokens == 16
    assert estimate.estimated_prompt_tokens == (estimate.estimated_content_tokens + 16)
    assert estimate.estimated_completion_tokens_upper_bound == 2048
    assert estimate.estimated_total_tokens_upper_bound == (
        estimate.estimated_prompt_tokens + 2048
    )


def test_update_detection_prompt_includes_thread_context():
    """标题和首楼作为背景传入，并明确只判断待检测消息。"""
    system_content, user_content = build_update_detection_prompt(
        thread_title="测试作品",
        first_message_content="这是作品首楼介绍",
        message_content="v2.0 已发布，修复若干问题",
        attachment_filenames=["settings.json"],
    )

    assert "标题和首楼内容仅用于帮助你理解作品背景" in system_content
    assert "必须只判断待检测消息" in system_content
    assert "帖子标题：\n测试作品" in user_content
    assert "帖子首楼内容：\n这是作品首楼介绍" in user_content
    assert "待检测消息：\nv2.0 已发布，修复若干问题" in user_content
    assert "附件文件名：settings.json" in user_content


def test_update_detector_ignores_legacy_enabled_config():
    """旧 enabled 即使为真，缺少 mode 时也保持 disabled。"""
    bot = MagicMock()
    bot.cache_service = MagicMock()

    detector = UpdateDetector(
        bot=bot,
        session_factory=MagicMock(),
        config={"update_detector": {"enabled": True}},
    )

    assert detector.mode == "disabled"
    assert detector.deepseek_service is None
    assert detector.token_stats_service is None


@pytest.mark.parametrize("invalid_mode", ["invalid", None, []])
def test_update_detector_treats_invalid_mode_as_disabled(invalid_mode):
    """非法或非字符串 mode 一律降级为 disabled。"""
    bot = MagicMock()
    bot.cache_service = MagicMock()

    detector = UpdateDetector(
        bot=bot,
        session_factory=MagicMock(),
        config={"update_detector": {"mode": invalid_mode}},
    )

    assert detector.mode == "disabled"
    assert detector.deepseek_service is None


def test_update_detector_skips_threads_younger_than_one_day():
    """帖子发布不满 24 小时时直接跳过更新检测。"""
    thread = MagicMock()
    thread.created_at = discord.utils.utcnow() - timedelta(hours=23)
    assert UpdateDetector._is_thread_too_new(thread) is True

    thread.created_at = discord.utils.utcnow() - timedelta(hours=25)
    assert UpdateDetector._is_thread_too_new(thread) is False


def test_update_detector_observe_mode_does_not_create_ai_client(monkeypatch):
    """observe 模式只初始化 Redis 统计，不创建 DeepSeek 客户端。"""
    redis = MagicMock()
    monkeypatch.setattr(
        "update_detector.cog.RedisManager.get_client",
        lambda: redis,
    )
    bot = MagicMock()
    bot.cache_service = MagicMock()

    detector = UpdateDetector(
        bot=bot,
        session_factory=MagicMock(),
        config={"update_detector": {"mode": "observe"}},
    )

    assert detector.mode == "observe"
    assert detector.deepseek_service is None
    assert detector.token_stats_service is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("thread_record", "expected_title", "expected_first_message_content"),
    [
        (
            ThreadModel(
                guild_id=1,
                channel_id=10,
                thread_id=30,
                title="数据库帖子标题",
                author_id=20,
                first_message_excerpt="数据库首楼内容",
            ),
            "数据库帖子标题",
            "数据库首楼内容",
        ),
        (None, "Discord 帖子标题", ""),
    ],
)
async def test_observe_message_only_records_estimate(
    monkeypatch,
    thread_record,
    expected_title,
    expected_first_message_content,
):
    """observe 候选消息使用帖子上下文估算，缺记录时按规则降级。"""
    redis = MagicMock()
    monkeypatch.setattr(
        "update_detector.cog.RedisManager.get_client",
        lambda: redis,
    )
    monkeypatch.setattr(
        "update_detector.cog.UserUpdatePreferenceRepository.get_preference",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "update_detector.cog.ThreadRepository.get_thread_with_tags",
        AsyncMock(return_value=thread_record),
    )
    bot = MagicMock()
    bot.cache_service.is_channel_indexed.return_value = True
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=MagicMock())
    session_context.__aexit__ = AsyncMock(return_value=None)
    session_factory = MagicMock(return_value=session_context)
    detector = UpdateDetector(
        bot=bot,
        session_factory=session_factory,
        config={"update_detector": {"mode": "observe"}},
    )
    detector.token_stats_service = MagicMock()
    detector.token_stats_service.record_estimate = AsyncMock()
    detector.do_sync_update = AsyncMock()

    fake_thread_type = type("FakeThread", (), {})
    monkeypatch.setattr("update_detector.cog.discord.Thread", fake_thread_type)
    thread = fake_thread_type()
    thread.parent_id = 10
    thread.owner_id = 20
    thread.id = 30
    thread.name = "Discord 帖子标题"
    message = MagicMock()
    message.guild = object()
    message.channel = thread
    message.author.bot = False
    message.author.id = 20
    message.id = 31
    message.content = "更新说明" * 30
    message.attachments = []

    await detector.on_message(message)

    detector.token_stats_service.record_estimate.assert_awaited_once()
    estimate_call = detector.token_stats_service.record_estimate.await_args.kwargs[
        "estimate"
    ]
    expected_system, expected_user = build_update_detection_prompt(
        thread_title=expected_title,
        first_message_content=expected_first_message_content,
        message_content=message.content,
    )
    expected_estimate = detector.token_estimator.estimate(
        system_content=expected_system,
        user_content=expected_user,
        max_output_tokens=detector.max_output_tokens,
    )
    assert estimate_call == expected_estimate
    detector.do_sync_update.assert_not_awaited()
    bot.api_scheduler.submit.assert_not_called()
    assert detector.deepseek_service is None


@pytest.mark.asyncio
async def test_deepseek_service_sends_thinking_request_and_reads_usage():
    """DeepSeek 请求使用确认后的 thinking 和输出上限并解析 usage。"""
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "YES",
                            "reasoning_content": "private reasoning",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 30,
                    "total_tokens": 150,
                },
            },
        )

    service = DeepSeekService(
        api_key="secret",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        thinking_enabled=True,
        max_output_tokens=2048,
        timeout_seconds=60,
    )
    await service._client.aclose()
    service._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    try:
        result = await service.detect_update("system", "user")
    finally:
        await service.close()

    assert captured_payload["model"] == "deepseek-v4-flash"
    assert captured_payload["thinking"] == {"type": "enabled"}
    assert captured_payload["max_tokens"] == 2048
    assert captured_payload["stream"] is False
    assert "temperature" not in captured_payload
    assert result.is_update is True
    assert result.prompt_tokens == 120
    assert result.completion_tokens == 30
    assert result.total_tokens == 150


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("finish_reason", "content", "expected_truncated"),
    [("length", "YES", True), ("stop", "MAYBE", False), ("stop", "", False)],
)
async def test_deepseek_service_rejects_truncated_or_invalid_decisions(
    finish_reason,
    content,
    expected_truncated,
):
    """截断、空内容及非严格 YES/NO 都不能触发更新。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": finish_reason,
                        "message": {"content": content},
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    service = DeepSeekService(
        api_key="secret",
        base_url="https://proxy.example/v1",
        model="deepseek-v4-flash",
        thinking_enabled=True,
        max_output_tokens=2048,
        timeout_seconds=60,
    )
    await service._client.aclose()
    service._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    try:
        result = await service.detect_update("system", "user")
    finally:
        await service.close()

    assert result.api_success is True
    assert result.decision is None
    assert result.truncated is expected_truncated
    assert result.is_update is False


@pytest.mark.asyncio
async def test_deepseek_service_handles_http_error_without_exposing_response():
    """DeepSeek 非成功状态返回静默失败结果。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "sensitive"}})

    service = DeepSeekService(
        api_key="secret",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        thinking_enabled=True,
        max_output_tokens=2048,
        timeout_seconds=60,
    )
    await service._client.aclose()
    service._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    try:
        result = await service.detect_update("system", "user")
    finally:
        await service.close()

    assert result.api_success is False
    assert result.is_update is False
    assert result.usage_missing is True


@pytest.mark.asyncio
async def test_token_stats_service_writes_daily_hash_and_fixed_expiry():
    """估算统计通过一个事务管道写入当日 Hash 并设置固定过期日。"""
    pipeline = MagicMock()
    pipeline.__aenter__ = AsyncMock(return_value=pipeline)
    pipeline.__aexit__ = AsyncMock(return_value=None)
    pipeline.execute = AsyncMock(return_value=[])
    redis = MagicMock()
    redis.pipeline.return_value = pipeline
    service = TokenStatsService(redis)
    estimate = TokenEstimate(
        ascii_character_count=8,
        non_ascii_character_count=10,
        estimated_content_tokens=12,
        chat_overhead_tokens=16,
        estimated_prompt_tokens=28,
        estimated_completion_tokens_upper_bound=2048,
        estimated_total_tokens_upper_bound=2076,
    )

    await service.record_estimate(
        model="deepseek-v4-flash",
        thinking_enabled=True,
        max_output_tokens=2048,
        estimate=estimate,
    )

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    expected_key = f"update_detector:token_stats:estimate:deepseek-v4-flash:{today}"
    redis.pipeline.assert_called_once_with(transaction=True)
    pipeline.hsetnx.assert_called_once_with(
        expected_key,
        "first_recorded_at",
        pipeline.hsetnx.call_args.args[2],
    )
    pipeline.hincrby.assert_any_call(expected_key, "eligible_request_count", 1)
    pipeline.hincrby.assert_any_call(expected_key, "estimated_prompt_tokens", 28)
    expiry_timestamp = pipeline.expireat.call_args.args[1]
    remaining_days = (
        datetime.fromtimestamp(expiry_timestamp, timezone.utc)
        - datetime.now(timezone.utc)
    ).days
    assert remaining_days in {89, 90}
    pipeline.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_token_stats_service_counts_actual_outcomes_and_usage():
    """正式统计区分有效判断、无效判断和真实 Token usage。"""
    pipeline = MagicMock()
    pipeline.__aenter__ = AsyncMock(return_value=pipeline)
    pipeline.__aexit__ = AsyncMock(return_value=None)
    pipeline.execute = AsyncMock(return_value=[])
    redis = MagicMock()
    redis.pipeline.return_value = pipeline
    service = TokenStatsService(redis)
    result = UpdateDetectionResult(
        api_success=True,
        decision="NO",
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
    )

    await service.record_actual(
        model="deepseek-v4-flash",
        thinking_enabled=True,
        max_output_tokens=2048,
        result=result,
    )

    key = pipeline.hincrby.call_args_list[0].args[0]
    pipeline.hincrby.assert_any_call(key, "request_attempt_count", 1)
    pipeline.hincrby.assert_any_call(key, "api_success_count", 1)
    pipeline.hincrby.assert_any_call(key, "decision_no_count", 1)
    pipeline.hincrby.assert_any_call(key, "usage_missing_count", 0)
    pipeline.hincrby.assert_any_call(key, "total_tokens", 120)


@pytest.mark.asyncio
async def test_update_detector_view_has_no_timeout_or_auto_delete_footer():
    """提醒不自动超时删除，Embed 也不再显示删除倒计时。"""
    view = UpdateDetectorView(
        cog=MagicMock(),
        thread_id=1,
        author_id=2,
        message_link="https://discord.example/message",
    )
    embed = build_update_embed("请确认", "帖子")

    assert view.timeout is None
    assert embed.footer.text is None


@pytest.mark.asyncio
async def test_update_detector_view_rejects_non_author_interaction():
    """非帖子作者不能操作更新检测提醒。"""
    view = UpdateDetectorView(
        cog=MagicMock(),
        thread_id=1,
        author_id=2,
        message_link="https://discord.example/message",
    )
    interaction = MagicMock()
    interaction.user.id = 3
    interaction.response.send_message = AsyncMock()

    allowed = await view._handle_interaction_check(interaction)

    assert allowed is False
    interaction.response.send_message.assert_awaited_once_with(
        "此操作仅帖子作者可用。",
        ephemeral=True,
    )
