import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from dto.open_graph import OpenGraphWorkCandidateDTO
from open_graph.image_resolver import OpenGraphImageResolver


def _discord_url(expiry_epoch: int, attachment_id: int = 456) -> str:
    """构造 Discord 签名附件 URL。"""
    return (
        f"https://cdn.discordapp.com/attachments/123/{attachment_id}/cover.png"
        f"?ex={expiry_epoch:x}&is=abc&hm=signature"
    )


async def _candidates(items: list[OpenGraphWorkCandidateDTO]):
    """把候选列表转换为测试所需的异步流。"""
    for item in items:
        yield item


def _resolver(queue: MagicMock, max_jobs: int = 5) -> OpenGraphImageResolver:
    """构造使用一小时刷新窗口的图片解析器。"""
    return OpenGraphImageResolver(queue, 3600, 2, max_jobs)


@pytest.mark.asyncio
async def test_url_with_more_than_one_hour_does_not_touch_queue():
    """有效期超过一小时的图片直接返回且不访问 Redis 队列。"""
    url = _discord_url(int(time.time()) + 7200)
    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock()

    result = await _resolver(queue).select_thread_image(
        42, [url], wait_for_refresh=True
    )

    assert result.image_url == url
    assert result.cache_ttl_limit_seconds is not None
    queue.get_or_enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_image_and_non_discord_image_do_not_enqueue():
    """无图帖子不入队，非 Discord 图片直接使用。"""
    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock()
    resolver = _resolver(queue)

    empty = await resolver.select_thread_image(41, [], wait_for_refresh=True)
    external = await resolver.select_thread_image(
        42,
        ["https://images.example.com/cover.png?version=1"],
        wait_for_refresh=True,
    )

    assert empty.image_url is None
    assert external.image_url == "https://images.example.com/cover.png?version=1"
    queue.get_or_enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_last_hour_returns_old_url_and_enqueues_without_waiting():
    """最后一小时仍返回旧 URL，同时异步入队而不等待结果。"""
    url = _discord_url(int(time.time()) + 1800)
    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock(return_value="job")
    queue.wait_for_result = AsyncMock()

    result = await _resolver(queue).select_thread_image(
        42, [url], wait_for_refresh=True
    )

    assert result.image_url == url
    assert result.refresh_attempted is True
    queue.get_or_enqueue.assert_awaited_once_with(42)
    queue.wait_for_result.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_first_image_falls_back_to_later_valid_image():
    """首图过期时继续检查同帖后续图片，并异步刷新该帖。"""
    expired = _discord_url(int(time.time()) - 60, 456)
    fresh = _discord_url(int(time.time()) + 7200, 789)
    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock(return_value="job")
    queue.wait_for_result = AsyncMock()

    result = await _resolver(queue).select_thread_image(
        42, [expired, fresh], wait_for_refresh=True
    )

    assert result.image_url == fresh
    assert result.refresh_attempted is True
    queue.get_or_enqueue.assert_awaited_once_with(42)
    queue.wait_for_result.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wait_result, should_reload",
    [({"status": "success"}, True), ({"status": "failed"}, False), (None, False)],
)
async def test_single_thread_waits_only_when_all_discord_images_are_stale(
    wait_result, should_reload
):
    """单帖全部失效时等待结果，只有明确成功才要求服务重查数据库。"""
    invalid = (
        "https://cdn.discordapp.com/attachments/123/456/cover.png"
        "?ex=invalid&is=abc&hm=signature"
    )
    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock(return_value="job")
    queue.wait_for_result = AsyncMock(return_value=wait_result)

    result = await _resolver(queue).select_thread_image(
        42, [invalid], wait_for_refresh=True
    )

    assert result.image_url is None
    assert result.should_reload is should_reload
    queue.wait_for_result.assert_awaited_once_with("job", 2)


@pytest.mark.asyncio
async def test_multi_work_scan_deduplicates_and_caps_refresh_jobs():
    """多作品扫描跳过重复身份，并把异步刷新限制在五个不同帖子。"""
    now = int(time.time())
    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock(return_value="job")
    candidates = []
    for index in range(7):
        candidates.append(
            OpenGraphWorkCandidateDTO(
                thread_id=100 + index,
                title=f"作品 {index}",
                thumbnail_urls=[_discord_url(now - 10, 1000 + index)],
                reaction_count=100 - index,
                created_at=datetime(2026, 8, 1),
            )
        )
    candidates.extend(
        [
            OpenGraphWorkCandidateDTO(
                thread_id=200,
                title="有效作品",
                thumbnail_urls=["https://example.com/a.png?x=1"],
                reaction_count=10,
                created_at=datetime(2026, 8, 1),
            ),
            OpenGraphWorkCandidateDTO(
                thread_id=201,
                title="重复图片",
                thumbnail_urls=["https://example.com/a.png?x=1"],
                reaction_count=9,
                created_at=datetime(2026, 8, 1),
            ),
            OpenGraphWorkCandidateDTO(
                thread_id=202,
                title="第二张有效图",
                thumbnail_urls=["https://example.com/b.png"],
                reaction_count=8,
                created_at=datetime(2026, 8, 1),
            ),
            OpenGraphWorkCandidateDTO(
                thread_id=203,
                title="第三张有效图",
                thumbnail_urls=["https://example.com/c.png"],
                reaction_count=7,
                created_at=datetime(2026, 8, 1),
            ),
            OpenGraphWorkCandidateDTO(
                thread_id=204,
                title="第四张有效图",
                thumbnail_urls=["https://example.com/d.png"],
                reaction_count=6,
                created_at=datetime(2026, 8, 1),
            ),
            OpenGraphWorkCandidateDTO(
                thread_id=205,
                title="第五张有效图",
                thumbnail_urls=["https://example.com/e.png"],
                reaction_count=5,
                created_at=datetime(2026, 8, 1),
            ),
            OpenGraphWorkCandidateDTO(
                thread_id=206,
                title="超出上限作品",
                thumbnail_urls=["https://example.com/f.png"],
                reaction_count=4,
                created_at=datetime(2026, 8, 1),
            ),
        ]
    )

    result = await _resolver(queue).select_works(_candidates(candidates))

    assert [work.title for work in result.works] == [
        "有效作品",
        "第二张有效图",
        "第三张有效图",
        "第四张有效图",
        "第五张有效图",
    ]
    assert result.source_thread_ids == [200, 202, 203, 204, 205]
    assert queue.get_or_enqueue.await_count == 5
