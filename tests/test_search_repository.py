"""
搜索排除场景测试（PostgreSQL 后端）。

此文件中的参数化测试由 test_search_comprehensive.py 的
TestExclusionParameterized 覆盖，保留此处作为互补验证。
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator, List, Set

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlmodel import delete
from shared.time_utils import utc_now

from models import Thread
from search.search_service import SearchService
from search.qo.thread_search import ThreadSearchQuery
from core.tag_cache_service import TagCacheService


@pytest_asyncio.fixture(scope="function")
async def seeded_db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """填充了测试数据的会话。"""
    async with db_session_factory() as session:
        await session.execute(delete(Thread))
        await session.commit()

        threads_to_create = [
            Thread(
                channel_id=1,
                thread_id=101,
                title="关于百合破坏的讨论",
                author_id=1,
                created_at=utc_now(),
            ),
            Thread(
                channel_id=1,
                thread_id=102,
                title="🈲百合破坏",
                author_id=2,
                created_at=utc_now(),
            ),
            Thread(
                channel_id=1,
                thread_id=103,
                title="小说推荐",
                author_id=3,
                created_at=utc_now(),
            ),
            Thread(
                channel_id=1,
                thread_id=104,
                title="禁：请勿讨论百合破坏话题",
                author_id=4,
                created_at=utc_now(),
            ),
            Thread(
                channel_id=1,
                thread_id=105,
                title="纯爱小说分享",
                author_id=5,
                created_at=utc_now(),
            ),
        ]
        session.add_all(threads_to_create)
        await session.commit()

        yield session

        await session.execute(delete(Thread))
        await session.commit()


@pytest.mark.parametrize(
    "test_id, exclude_keywords, exemption_markers, expected_count, expected_present, expected_absent",
    [
        (
            "1_full_word_with_exemption",
            "百合破坏",
            ["禁", "🈲"],
            4,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论"},
        ),
        (
            "2_prefix_with_exemption",
            "百合破",
            ["禁", "🈲"],
            4,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论"},
        ),
        (
            "3_general_prefix_with_exemption",
            "百合",
            ["禁", "🈲"],
            4,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论"},
        ),
        (
            "4_full_word_no_exemption",
            "百合破坏",
            [],
            2,
            {"小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论", "🈲百合破坏", "禁：请勿讨论百合破坏话题"},
        ),
        (
            "5_prefix_no_exemption",
            "百合破",
            [],
            2,
            {"小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论", "🈲百合破坏", "禁：请勿讨论百合破坏话题"},
        ),
        (
            "6_multiple_keywords_or_logic",
            "百合破坏 小说",
            [],
            0,
            set(),
            {
                "关于百合破坏的讨论",
                "🈲百合破坏",
                "禁：请勿讨论百合破坏话题",
                "小说推荐",
                "纯爱小说分享",
            },
        ),
        (
            "7_multiple_keywords_with_exemption",
            "百合破坏 纯爱",
            ["禁", "🈲"],
            3,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐"},
            {"关于百合破坏的讨论", "纯爱小说分享"},
        ),
    ],
)
@pytest.mark.asyncio
async def test_search_exclusion_scenarios(
    seeded_db_session: AsyncSession,
    db_session_factory: async_sessionmaker[AsyncSession],
    test_id: str,
    exclude_keywords: str,
    exemption_markers: List[str],
    expected_count: int,
    expected_present: Set[str],
    expected_absent: Set[str],
):
    """对反选关键词的各种场景进行参数化测试。"""
    tag_service = TagCacheService(session_factory=db_session_factory)
    await tag_service.build_cache()
    repo = SearchService(session=seeded_db_session, tag_cache_service=tag_service)

    query = ThreadSearchQuery(
        exclude_keywords=exclude_keywords,
        exclude_keyword_exemption_markers=exemption_markers,
    )

    threads, total_threads = await repo.search_threads_with_count(
        query=query,
        offset=0,
        limit=10,
        total_display_count=1000,
        exploration_factor=1.414,
        strength_weight=10.0,
    )

    returned_titles = {t.title for t in threads}

    print(f"--- 运行测试: {test_id} ---")
    print(f"排除关键词: '{exclude_keywords}'")
    print(f"返回的标题: {returned_titles}")
    print(f"预期数量: {expected_count}, 实际: {total_threads}")
    print(f"预期存在: {expected_present}")
    print(f"预期不存在: {expected_absent}")

    assert total_threads == expected_count, f"测试 '{test_id}' 失败：总数不匹配"
    assert returned_titles.issuperset(expected_present), (
        f"测试 '{test_id}' 失败：部分预期结果缺失"
    )
    assert not returned_titles.intersection(expected_absent), (
        f"测试 '{test_id}' 失败：返回了不应出现的结果"
    )
