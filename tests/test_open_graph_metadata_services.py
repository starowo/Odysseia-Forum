import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from models import Author, Booklist, BooklistItem, Thread
from core.thread_repository import ThreadRepository
from dto.open_graph import (
    AuthorShareMetadataDTO,
    AuthorShareStatsDTO,
)
from open_graph.author_open_graph_service import AuthorOpenGraphService
from open_graph.booklist_open_graph_service import BooklistOpenGraphService
from open_graph.image_resolver import OpenGraphImageResolver
from open_graph.thread_open_graph_service import ThreadOpenGraphService


def _cache_miss() -> MagicMock:
    """构造始终未命中的元数据缓存替身。"""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.invalidate = AsyncMock()
    return cache


def _image_resolver() -> OpenGraphImageResolver:
    """构造不访问真实 Redis 的图片解析器。"""
    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock(return_value="job")
    queue.wait_for_result = AsyncMock(return_value=None)
    return OpenGraphImageResolver(queue, 3600, 2, 5)


def _discord_url(expiry_epoch: int) -> str:
    """构造供服务集成测试使用的 Discord 签名图片 URL。"""
    return (
        "https://cdn.discordapp.com/attachments/123/456/cover.png"
        f"?ex={expiry_epoch:x}&is=abc&hm=signature"
    )


@pytest.mark.asyncio
async def test_thread_service_filters_visibility_and_serializes_utc_z(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """帖子服务隐藏失效与深渊资源，并使用最后活跃时间输出 UTC Z。"""
    created_at = datetime(2026, 8, 1, 1, 2, 3)
    last_active_at = created_at + timedelta(days=1)
    async with db_session_factory() as session:
        session.add(
            Author(
                id=8001,
                name="author",
                display_name=" **作者** ",
                last_updated=created_at,
            )
        )
        session.add_all(
            [
                Thread(
                    channel_id=10,
                    thread_id=8101,
                    title="<b>公开帖子</b>",
                    first_message_excerpt="[简介](https://example.com)",
                    author_id=8001,
                    created_at=created_at,
                    last_active_at=last_active_at,
                    thumbnail_urls=["https://example.com/thread.png"],
                ),
                Thread(
                    channel_id=99,
                    thread_id=8102,
                    title="深渊帖子",
                    author_id=8001,
                    created_at=created_at,
                ),
                Thread(
                    channel_id=10,
                    thread_id=8103,
                    title="隐藏帖子",
                    author_id=8001,
                    created_at=created_at,
                    show_flag=False,
                ),
            ]
        )
        await session.commit()

    service = ThreadOpenGraphService(
        db_session_factory, _image_resolver(), _cache_miss(), {99}
    )
    public = await service.get_share_metadata(8101)

    assert public is not None
    assert public.title == "公开帖子"
    assert public.description == "简介"
    assert public.author.display_name == "作者"
    assert public.model_dump(mode="json")["updated_at"].endswith("Z")
    assert await service.get_share_metadata(8102) is None
    assert await service.get_share_metadata(8103) is None


@pytest.mark.asyncio
async def test_author_service_uses_public_stats_independent_latest_and_stable_works(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """作者统计与最新作品过滤公开范围，代表作品按固定热度顺序选图。"""
    base = datetime(2026, 8, 1)
    async with db_session_factory() as session:
        session.add(
            Author(
                id=8201,
                name="author",
                display_name="作者",
                last_updated=base,
            )
        )
        session.add_all(
            [
                Thread(
                    channel_id=10,
                    thread_id=8211,
                    title="高热度作品",
                    author_id=8201,
                    created_at=base,
                    reaction_count=20,
                    reply_count=2,
                    thumbnail_urls=["https://example.com/hot.png"],
                ),
                Thread(
                    channel_id=10,
                    thread_id=8212,
                    title="最新无图作品",
                    author_id=8201,
                    created_at=base + timedelta(days=2),
                    reaction_count=1,
                    reply_count=3,
                    thumbnail_urls=[],
                ),
                Thread(
                    channel_id=10,
                    thread_id=8215,
                    title="同分第二作品",
                    author_id=8201,
                    created_at=base,
                    reaction_count=20,
                    reply_count=4,
                    thumbnail_urls=["https://example.com/tied.png"],
                ),
                Thread(
                    channel_id=99,
                    thread_id=8213,
                    title="深渊高热度",
                    author_id=8201,
                    created_at=base + timedelta(days=3),
                    reaction_count=999,
                    reply_count=999,
                    thumbnail_urls=["https://example.com/abyss.png"],
                ),
                Thread(
                    channel_id=10,
                    thread_id=8214,
                    title="隐藏高热度",
                    author_id=8201,
                    created_at=base + timedelta(days=4),
                    reaction_count=999,
                    show_flag=False,
                    thumbnail_urls=["https://example.com/hidden.png"],
                ),
            ]
        )
        await session.commit()

    service = AuthorOpenGraphService(
        db_session_factory, _image_resolver(), _cache_miss(), {99}
    )
    result = await service.get_share_metadata(8201)

    assert result is not None
    assert result.stats.thread_count == 3
    assert result.stats.reaction_count == 41
    assert result.stats.reply_count == 9
    assert result.latest_work is not None
    assert result.latest_work.title == "最新无图作品"
    assert [work.title for work in result.works] == ["高热度作品", "同分第二作品"]


@pytest.mark.asyncio
async def test_author_without_public_work_returns_404_semantics(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """存在作者记录但没有公开作品时服务返回空结果供路由映射 404。"""
    async with db_session_factory() as session:
        session.add(
            Author(
                id=8301,
                name="empty",
                display_name="空作者",
                last_updated=datetime(2026, 8, 1),
            )
        )
        await session.commit()

    service = AuthorOpenGraphService(
        db_session_factory, _image_resolver(), _cache_miss(), set()
    )

    assert await service.get_share_metadata(8301) is None


@pytest.mark.asyncio
async def test_author_cache_source_must_still_belong_to_author(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """作者缓存来源改属其他作者时删除缓存并重建真实响应。"""
    base = datetime(2026, 8, 1)
    async with db_session_factory() as session:
        session.add_all(
            [
                Author(
                    id=8351,
                    name="target",
                    display_name="真实作者",
                    last_updated=base,
                ),
                Author(
                    id=8352,
                    name="other",
                    display_name="其他作者",
                    last_updated=base,
                ),
                Thread(
                    channel_id=10,
                    thread_id=83511,
                    title="真实作品",
                    author_id=8351,
                    created_at=base,
                    thumbnail_urls=["https://example.com/real.png"],
                ),
                Thread(
                    channel_id=10,
                    thread_id=83521,
                    title="其他作品",
                    author_id=8352,
                    created_at=base,
                    thumbnail_urls=["https://example.com/other.png"],
                ),
            ]
        )
        await session.commit()

    cached = AuthorShareMetadataDTO(
        display_name="过期缓存",
        stats=AuthorShareStatsDTO(thread_count=1, reaction_count=0, reply_count=0),
        works=[],
        updated_at=base,
    )
    cache = MagicMock()
    cache.get = AsyncMock(return_value=(cached, [83521]))
    cache.invalidate = AsyncMock()
    cache.set = AsyncMock()
    service = AuthorOpenGraphService(
        db_session_factory, _image_resolver(), cache, set()
    )

    result = await service.get_share_metadata(8351)

    assert result is not None and result.display_name == "真实作者"
    cache.invalidate.assert_awaited_once_with("author", 8351)


@pytest.mark.asyncio
async def test_booklist_service_counts_visible_items_and_deduplicates_cover(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """书单实时统计可见成员，自定义封面参与作品图片跨字段去重。"""
    base = datetime(2026, 8, 1)
    cover = "https://example.com/cover.png"
    async with db_session_factory() as session:
        session.add(
            Author(
                id=8401,
                name="owner",
                display_name=" **书单主** ",
                last_updated=base,
            )
        )
        booklist = Booklist(
            owner_id=8401,
            title="<b>测试书单</b>",
            description="[书单简介](https://example.com)",
            cover_image_url=cover,
            is_public=True,
            item_count=99,
            collection_count=4,
            view_count=8,
            created_at=base,
            updated_at=base,
        )
        session.add(booklist)
        await session.flush()
        assert booklist.id is not None
        booklist_id = booklist.id
        threads = [
            Thread(
                channel_id=10,
                thread_id=8411,
                title="封面重复作品",
                author_id=8401,
                created_at=base,
                reaction_count=30,
                thumbnail_urls=[cover],
            ),
            Thread(
                channel_id=10,
                thread_id=8412,
                title="有效作品",
                author_id=8401,
                created_at=base,
                reaction_count=20,
                thumbnail_urls=["https://example.com/work.png"],
            ),
            Thread(
                channel_id=99,
                thread_id=8413,
                title="深渊作品",
                author_id=8401,
                created_at=base,
                reaction_count=100,
                thumbnail_urls=["https://example.com/abyss.png"],
            ),
            Thread(
                channel_id=10,
                thread_id=8414,
                title="失效作品",
                author_id=8401,
                created_at=base,
                not_found_count=1,
                thumbnail_urls=["https://example.com/missing.png"],
            ),
        ]
        session.add_all(threads)
        session.add_all(
            [
                BooklistItem(booklist_id=booklist_id, thread_id=item.thread_id)
                for item in threads
            ]
        )
        await session.commit()

    service = BooklistOpenGraphService(
        db_session_factory, _image_resolver(), _cache_miss(), {99}
    )
    result = await service.get_share_metadata(booklist_id)

    assert result is not None
    assert result.title == "测试书单"
    assert result.description == "书单简介"
    assert result.author_name == "书单主"
    assert result.cover_image_url == cover
    assert result.stats.item_count == 2
    assert [work.title for work in result.works] == ["有效作品"]
    assert "image_url" not in result.model_dump()
    assert "item_count" not in result.model_dump()


@pytest.mark.asyncio
async def test_public_empty_anonymous_tournament_booklist_returns_200_shape(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """公开空赛事书单返回空作品、实时零计数且隐藏匿名作者。"""
    async with db_session_factory() as session:
        booklist = Booklist(
            owner_id=9999,
            title="赛事",
            cover_image_url=_discord_url(int(time.time()) - 60),
            is_public=True,
            is_anonymous=True,
            is_tournament=True,
        )
        session.add(booklist)
        await session.commit()
        await session.refresh(booklist)
        booklist_id = booklist.id

    service = BooklistOpenGraphService(
        db_session_factory, _image_resolver(), _cache_miss(), set()
    )
    result = await service.get_share_metadata(booklist_id)

    assert result is not None
    assert result.works == []
    assert result.stats.item_count == 0
    assert result.cover_image_url == booklist.cover_image_url
    assert result.author_name is None
    assert result.is_tournament is True


@pytest.mark.asyncio
async def test_private_and_missing_booklists_are_indistinguishable(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """私有书单与不存在书单都返回空结果供路由统一映射为 404。"""
    async with db_session_factory() as session:
        booklist = Booklist(
            owner_id=8501,
            title="私有书单",
            is_public=False,
        )
        session.add(booklist)
        await session.commit()
        await session.refresh(booklist)
        booklist_id = booklist.id

    cache = _cache_miss()
    service = BooklistOpenGraphService(
        db_session_factory, _image_resolver(), cache, set()
    )

    assert await service.get_share_metadata(booklist_id) is None
    assert await service.get_share_metadata(999999) is None
    cache.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_thread_success_notification_requeries_and_validates_database_url(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """Bot 成功通知后单帖服务重查数据库，并只返回新写入的有效 URL。"""
    stale_url = _discord_url(int(time.time()) - 60)
    fresh_url = _discord_url(int(time.time()) + 7200)
    async with db_session_factory() as session:
        session.add(
            Thread(
                channel_id=10,
                thread_id=8601,
                title="等待刷新帖子",
                author_id=8600,
                created_at=datetime(2026, 8, 1),
                thumbnail_urls=[stale_url],
            )
        )
        await session.commit()

    async def update_database_before_success(job_id, timeout_seconds):
        assert job_id == "job" and timeout_seconds == 2
        async with db_session_factory() as session:
            await ThreadRepository(session).update_thread_thumbnail_urls(
                8601, [fresh_url]
            )
        return {"status": "success", "thread_id": "8601"}

    queue = MagicMock()
    queue.get_or_enqueue = AsyncMock(return_value="job")
    queue.wait_for_result = AsyncMock(side_effect=update_database_before_success)
    resolver = OpenGraphImageResolver(queue, 3600, 2, 5)
    cache = _cache_miss()
    service = ThreadOpenGraphService(db_session_factory, resolver, cache, set())

    result = await service.get_share_metadata(8601)

    assert result is not None and result.image_url == fresh_url
    cache.set.assert_not_awaited()
