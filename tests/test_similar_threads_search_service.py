from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.tag_cache_service import TagCacheService
from core.thread_repository import ThreadRepository
from dto.preferences import UserSearchPreferencesDTO
from dto.search import SearchConfigDTO
from models import Tag, Thread, TagBinding
from search.search_service import SearchService


@pytest.mark.asyncio
async def test_candidate_pool_and_live_preference_ranking(
    db_session_factory: async_sessionmaker[AsyncSession],
):
    """候选池保留匹配层级，返回时应用反选偏好并按层级优先排序。"""
    now = datetime.now()
    common = Tag(id=8101, name="共同")
    niche = Tag(id=8102, name="细分")
    excluded = Tag(id=8103, name="反选")
    threads = [
        Thread(
            thread_id=9100,
            channel_id=10,
            title="源帖",
            author_id=1,
            created_at=now,
        ),
        Thread(
            thread_id=9101,
            channel_id=10,
            title="精确匹配但较冷",
            author_id=2,
            reaction_count=1,
            created_at=now - timedelta(days=30),
        ),
        Thread(
            thread_id=9102,
            channel_id=10,
            title="包含雷点的精确匹配",
            author_id=3,
            reaction_count=20,
            created_at=now,
        ),
        Thread(
            thread_id=9103,
            channel_id=10,
            title="宽松匹配但很热门",
            author_id=5,
            reaction_count=1000,
            created_at=now,
        ),
        Thread(
            thread_id=9104,
            channel_id=10,
            title="应按作者排除",
            author_id=4,
            reaction_count=100,
            created_at=now,
        ),
        Thread(
            thread_id=9105,
            channel_id=10,
            title="应按标签排除",
            author_id=6,
            reaction_count=100,
            created_at=now,
        ),
        Thread(
            thread_id=9106,
            channel_id=10,
            title="没有标签的合法源帖",
            author_id=7,
            created_at=now,
        ),
    ]

    async with db_session_factory() as session:
        session.add_all([common, niche, excluded, *threads])
        await session.flush()
        internal_ids = {thread.thread_id: thread.id for thread in threads}
        links = {
            9100: [8101, 8102],
            9101: [8101, 8102],
            9102: [8101, 8102],
            9103: [8101],
            9104: [8101],
            9105: [8101, 8103],
        }
        session.add_all(
            TagBinding(
                target_type="thread",
                binding_source="local",
                target_id=internal_ids[thread_id],
                tag_id=tag_id,
            )
            for thread_id, tag_ids in links.items()
            for tag_id in tag_ids
        )
        await session.commit()

    tag_cache = TagCacheService(db_session_factory)
    await tag_cache.build_cache()
    config = SearchConfigDTO(reddit_hot_time_decay=45_000)

    async with db_session_factory() as session:
        thread_repo = ThreadRepository(session)
        assert await thread_repo.is_thread_searchable(9100) is True
        assert await thread_repo.is_thread_searchable(9100, [10]) is False

        service = SearchService(session, tag_cache)
        candidates, complete = await service.build_similar_thread_candidates(
            9100,
            candidate_limit=200,
            exclude_channel_ids=None,
            ucb1_config=config,
            timeout_seconds=5,
        )
        (
            empty_candidates,
            empty_complete,
        ) = await service.build_similar_thread_candidates(
            9106,
            candidate_limit=200,
            exclude_channel_ids=None,
            ucb1_config=config,
            timeout_seconds=5,
        )

    assert complete is True
    assert empty_complete is True
    assert empty_candidates == []
    levels = {
        candidate.thread_id: candidate.matched_tag_count for candidate in candidates
    }
    assert levels == {9101: 2, 9102: 2, 9103: 1, 9104: 1, 9105: 1}

    prefs = UserSearchPreferencesDTO(
        user_id=99,
        preferred_channels=[999],
        include_authors=[999],
        include_tags=["不存在"],
        include_keywords="不存在",
        exclude_authors=[4],
        exclude_tags=["反选"],
        exclude_keywords="雷点",
        exclude_keyword_exemption_markers=[],
    )
    async with db_session_factory() as session:
        service = SearchService(session, tag_cache)
        results, matched_tag_count = await service.filter_and_rank_similar_candidates(
            candidates,
            limit=10,
            prefs=prefs,
            exclude_channel_ids=None,
            time_decay=config.reddit_hot_time_decay,
        )

    # 正选偏好不会收窄相似推荐；两 TAG 的冷帖仍优先于一 TAG 的热门帖。
    assert [thread.thread_id for thread in results] == [9101, 9103]
    assert matched_tag_count == 1
