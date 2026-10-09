"""THREAD_MEMBERS_UPDATE 窄范围兼容补丁的测试。"""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import discord
import pytest

from core.discord_parser_patch import install_uncached_thread_members_patch


def make_payload(**overrides):
    """构造最小可用的线程成员更新载荷，便于各测试按需覆写字段。"""
    payload = {
        "guild_id": "100",
        "id": "200",
        "member_count": 1,
        "removed_member_ids": ["300"],
    }
    payload.update(overrides)
    return payload


def make_bot(*, guild, parsers=None):
    """构造仅包含补丁安装所需接口的 Bot 替身。"""
    original_parser = MagicMock()
    if parsers is None:
        parsers = {"THREAD_MEMBERS_UPDATE": original_parser}

    bot = MagicMock()
    bot._connection = SimpleNamespace(parsers=parsers)
    bot.get_guild.return_value = guild
    return bot, original_parser


def test_cached_thread_delegates_to_original_parser():
    # 已缓存帖子应继续沿用 discord.py 原解析流程，避免重复派发事件。
    guild = MagicMock()
    guild.get_thread.return_value = object()
    bot, original_parser = make_bot(guild=guild)
    payload = make_payload()

    assert install_uncached_thread_members_patch(bot) is True
    bot._connection.parsers["THREAD_MEMBERS_UPDATE"](payload)

    original_parser.assert_called_once_with(payload)
    bot.dispatch.assert_not_called()


def test_uncached_thread_dispatches_raw_remove_without_delegating():
    # 未缓存帖子应补发 raw 事件，并且不再调用原解析器的提前返回逻辑。
    guild = MagicMock()
    guild.get_thread.return_value = None
    bot, original_parser = make_bot(guild=guild)
    payload = make_payload()

    assert install_uncached_thread_members_patch(bot) is True
    bot._connection.parsers["THREAD_MEMBERS_UPDATE"](payload)

    original_parser.assert_not_called()
    bot.dispatch.assert_called_once()
    event_name, raw_payload = bot.dispatch.call_args.args
    assert event_name == "raw_thread_member_remove"
    assert isinstance(raw_payload, discord.RawThreadMembersUpdate)
    assert raw_payload.data is payload
    assert raw_payload.guild_id == 100
    assert raw_payload.thread_id == 200


@pytest.mark.parametrize(
    "guild,payload",
    [
        (None, make_payload()),
        (MagicMock(), make_payload(removed_member_ids=[])),
        (
            MagicMock(),
            make_payload(
                removed_member_ids=[],
                added_members=[{"user_id": "300"}],
            ),
        ),
    ],
)
def test_non_target_events_delegate_without_dispatch(guild, payload):
    # 非目标场景不应误补发事件，包括未知服务器、空移除列表和仅新增成员。
    bot, original_parser = make_bot(guild=guild)

    assert install_uncached_thread_members_patch(bot) is True
    bot._connection.parsers["THREAD_MEMBERS_UPDATE"](payload)

    original_parser.assert_called_once_with(payload)
    bot.dispatch.assert_not_called()


def test_missing_parser_logs_error_without_raising(caplog):
    # 内部扩展点缺失时只记录错误，Bot 初始化流程仍需继续。
    bot, _ = make_bot(guild=None, parsers={})

    with caplog.at_level(logging.ERROR):
        installed = install_uncached_thread_members_patch(bot)

    assert installed is False
    assert bot._connection.parsers == {}
    assert "Bot 将继续启动" in caplog.text
    assert discord.__version__ in caplog.text


def test_parser_assignment_failure_logs_error_without_raising(caplog):
    # 即使 parser 映射不可写，也必须保持降级可用而不是中断启动。
    original_parser = MagicMock()

    class RejectingParsers(dict):
        def __setitem__(self, key, value):
            raise RuntimeError("read-only parser mapping")

    parsers = RejectingParsers({"THREAD_MEMBERS_UPDATE": original_parser})
    bot, _ = make_bot(guild=None, parsers=parsers)

    with caplog.at_level(logging.ERROR):
        installed = install_uncached_thread_members_patch(bot)

    assert installed is False
    assert parsers["THREAD_MEMBERS_UPDATE"] is original_parser
    assert "read-only parser mapping" in caplog.text


def test_wrapper_failure_falls_back_to_original_parser(caplog):
    # 包装后的补丁运行异常时，应立即回退到原解析器以保护主流程。
    guild = MagicMock()
    guild.get_thread.side_effect = RuntimeError("unexpected guild API")
    bot, original_parser = make_bot(guild=guild)
    payload = make_payload()

    assert install_uncached_thread_members_patch(bot) is True
    with caplog.at_level(logging.ERROR):
        bot._connection.parsers["THREAD_MEMBERS_UPDATE"](payload)

    original_parser.assert_called_once_with(payload)
    assert "已回退 discord.py 原解析器" in caplog.text
