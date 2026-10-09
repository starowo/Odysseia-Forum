"""
发现页仓库集成测试（PostgreSQL 后端）。

覆盖 discovery.py API 背后的数据层：
- DiscoveryRepository.get_latest_threads
- ThreadRepository.get_random_threads

PG 关注点：func.random() 排序，多表 JOIN，selectinload/joinedload
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models import Thread, Author, Tag, TagBinding
from discovery.discovery_repository import DiscoveryRepository
from core.thread_repository import ThreadRepository
from shared.time_utils import utc_now


@pytest_asyncio.fixture(scope="function")
async def discovery_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供已清理的独立会话。"""
    async with db_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seeded_discovery_session(
    discovery_session: AsyncSession,
) -> AsyncSession:
    """预填充多样化的帖子数据，用于发现页测试。"""
    # 创建作者
    authors = [
        Author(
            id=1,
            name="Author1",
            display_name="ADisp1",
            avatar_url="https://example.com/a1.png",
        ),
        Author(
            id=2,
            name="Author2",
            display_name="ADisp2",
            avatar_url="https://example.com/a2.png",
        ),
        Author(
            id=3,
            name="Author3",
            display_name="ADisp3",
            avatar_url="https://example.com/a3.png",
        ),
    ]
    discovery_session.add_all(authors)

    # 创建标签
    tags = [Tag(id=1, name="百合"), Tag(id=2, name="纯爱"), Tag(id=3, name="后宫")]
    discovery_session.add_all(tags)

    # 创建帖子（不同频道、不同时间）
    threads = [
        Thread(
            channel_id=1,
            thread_id=101,
            title="Latest Thread",
            author_id=1,
            created_at=utc_now(),
            show_flag=True,
            not_found_count=0,
        ),
        Thread(
            channel_id=1,
            thread_id=102,
            title="Hidden Thread",
            author_id=2,
            created_at=utc_now(),
            show_flag=False,
            not_found_count=0,
        ),
        Thread(
            channel_id=1,
            thread_id=103,
            title="NotFound Thread",
            author_id=3,
            created_at=utc_now(),
            show_flag=True,
            not_found_count=5,
        ),
        Thread(
            channel_id=2,
            thread_id=201,
            title="Channel 2 Thread",
            author_id=1,
            created_at=utc_now(),
            show_flag=True,
            not_found_count=0,
        ),
        Thread(
            channel_id=1,
            thread_id=104,
            title="Reaction Thread",
            author_id=2,
            created_at=utc_now(),
            show_flag=True,
            not_found_count=0,
            reaction_count=50,
        ),
    ]
    discovery_session.add_all(threads)
    await discovery_session.commit()

    # 获取内部 ID → 直接创建 TagBinding（TagBinding.thread_id = Thread.id）
    for t in threads:
        await discovery_session.refresh(t)
    id_map = {t.thread_id: t.id for t in threads}

    links = [
        TagBinding(
            target_type="thread",
            binding_source="local",
            target_id=id_map[101],
            tag_id=1,
        ),
        TagBinding(
            target_type="thread",
            binding_source="local",
            target_id=id_map[101],
            tag_id=2,
        ),
        TagBinding(
            target_type="thread",
            binding_source="local",
            target_id=id_map[201],
            tag_id=3,
        ),
    ]
    discovery_session.add_all(links)
    await discovery_session.commit()
    return discovery_session


@pytest.mark.asyncio
class TestGetLatestThreads:
    """获取最新帖子 — 过滤 + 排序"""

    async def test_get_latest_threads_basic(
        self, seeded_discovery_session: AsyncSession
    ):
        """基本拉取：排除隐藏/软删除帖子"""
        repo = DiscoveryRepository(seeded_discovery_session)
        threads = await repo.get_latest_threads(limit=10, offset=0, prefs=None)
        # 应包含: 101(Latest), 201(Ch2), 104(Reaction)
        # 排除: 102(Hidden, show_flag=False), 103(NotFound, not_found_count=5)
        thread_ids = {t.thread_id for t in threads}
        assert 101 in thread_ids
        assert 201 in thread_ids
        assert 104 in thread_ids
        assert 102 not in thread_ids
        assert 103 not in thread_ids

    async def test_get_latest_threads_limit(
        self, seeded_discovery_session: AsyncSession
    ):
        """分页限制"""
        repo = DiscoveryRepository(seeded_discovery_session)
        threads = await repo.get_latest_threads(limit=2, offset=0, prefs=None)
        assert len(threads) == 2

    async def test_get_latest_threads_offset(
        self, seeded_discovery_session: AsyncSession
    ):
        """偏移分页"""
        repo = DiscoveryRepository(seeded_discovery_session)
        page1 = await repo.get_latest_threads(limit=2, offset=0, prefs=None)
        page2 = await repo.get_latest_threads(limit=2, offset=2, prefs=None)
        all_ids = {t.thread_id for t in page1} | {t.thread_id for t in page2}
        # 应看到所有 3 个可见帖子
        assert len(all_ids) == 3

    async def test_get_latest_threads_eager_loading(
        self, seeded_discovery_session: AsyncSession
    ):
        """预加载 author 关系"""
        repo = DiscoveryRepository(seeded_discovery_session)
        threads = await repo.get_latest_threads(limit=10, offset=0, prefs=None)

        # 验证 author 被预加载（不触发 lazy load）
        for t in threads:
            if t.thread_id == 101:
                assert t.author is not None
                assert t.author.name == "Author1"

    async def test_get_latest_with_preferences_channel(
        self, seeded_discovery_session: AsyncSession
    ):
        """偏好过滤 → preferred_channels"""
        from dto.preferences.user_search_preferences_dto import UserSearchPreferencesDTO

        prefs = UserSearchPreferencesDTO(
            user_id=1,
            preferred_channels=[2],  # 只看 channel 2
        )
        repo = DiscoveryRepository(seeded_discovery_session)
        threads = await repo.get_latest_threads(limit=10, offset=0, prefs=prefs)
        thread_ids = {t.thread_id for t in threads}
        assert thread_ids == {201}  # 只有 channel 2 的帖子

    async def test_get_latest_with_explicit_channels(
        self, seeded_discovery_session: AsyncSession
    ):
        """显式频道范围使用 OR 匹配并在数据库层生效。"""
        repo = DiscoveryRepository(seeded_discovery_session)
        threads = await repo.get_latest_threads(
            limit=10,
            offset=0,
            prefs=None,
            channel_ids=[2],
        )
        assert {thread.thread_id for thread in threads} == {201}

    async def test_get_latest_with_empty_explicit_scope(
        self, seeded_discovery_session: AsyncSession
    ):
        """显式空频道范围不能退化为全频道查询。"""
        repo = DiscoveryRepository(seeded_discovery_session)
        threads = await repo.get_latest_threads(
            limit=10,
            offset=0,
            prefs=None,
            channel_ids=[],
        )
        assert threads == []

    async def test_get_ordered_threads_with_channel_filter(
        self, seeded_discovery_session: AsyncSession
    ):
        """趋势详情频道过滤后继续保持 Redis 成员顺序。"""
        repo = DiscoveryRepository(seeded_discovery_session)
        threads = await repo.get_threads_by_ids_ordered(
            [201, 104, 101],
            prefs=None,
            channel_ids=[1],
        )
        assert [thread.thread_id for thread in threads] == [104, 101]


class TestDiscoveryChannelResolution:
    """Rails 路由频道映射与偏好覆盖规则。"""

    def test_resolve_parent_channel_and_ignored_channels(self, monkeypatch):
        """目标频道展开来源频道后继续排除 discovery ignore 配置。"""
        from api.v1.routers import discovery as discovery_router

        class CacheStub:
            """提供路由频道解析需要的最小缓存接口。"""

            def get_indexed_channel_ids_list(self):
                """返回测试中的全部索引频道。"""
                return [10, 11, 12, 99]

        monkeypatch.setattr(discovery_router, "cache_service_instance", CacheStub())
        monkeypatch.setattr(
            discovery_router,
            "channel_mappings_config",
            {10: [{"tag_name": "映射", "source_channel_ids": [11, 12]}]},
        )
        monkeypatch.setattr(discovery_router, "discovery_ignore_channel_ids", [12])

        result = discovery_router._resolve_rails_channel_ids([10])

        assert result == [10, 11]

    def test_explicit_channels_override_only_channel_preference(self):
        """显式频道覆盖 preferred_channels，但保留其他偏好。"""
        from api.v1.routers import discovery as discovery_router
        from dto.preferences.user_search_preferences_dto import (
            UserSearchPreferencesDTO,
        )

        prefs = UserSearchPreferencesDTO(
            user_id=1,
            preferred_channels=[2],
            exclude_authors=[9],
            include_tags=["百合"],
        )

        result = discovery_router._override_preferred_channels(prefs, [1])

        assert result is not prefs
        assert result.preferred_channels is None
        assert result.exclude_authors == [9]
        assert result.include_tags == ["百合"]


@pytest.mark.asyncio
class TestDiscoveryServiceChannelSurge:
    """频道趋势子榜的有限补偿和参数传递。"""

    async def test_surge_retry_uses_channel_scope_and_rank_offsets(self):
        """过滤不足时沿同一频道子榜补偿，且最多按批次向后读取。"""
        from types import SimpleNamespace

        from discovery.discovery_service import DiscoveryService

        class TrendServiceStub:
            """按 offset 返回可预测的趋势成员。"""

            def __init__(self):
                self.calls = []

            async def get_top_surging_ids(
                self,
                metric,
                days,
                limit,
                offset=0,
                channel_ids=None,
            ):
                """记录调用并返回两批测试排名。"""
                self.calls.append((metric, days, limit, offset, channel_ids))
                if offset == 0:
                    return [1, 2, 3, 4, 5, 6]
                if offset == 6:
                    return [7, 8]
                return []

        class RepositoryStub:
            """模拟其他偏好过滤掉大部分第一批成员。"""

            def __init__(self):
                self.calls = []

            async def get_threads_by_ids_ordered(
                self, thread_ids, prefs, channel_ids=None
            ):
                """返回仍满足其他偏好的帖子并保持输入顺序。"""
                self.calls.append((thread_ids, prefs, channel_ids))
                allowed_ids = {3, 7, 8}
                return [
                    SimpleNamespace(thread_id=thread_id)
                    for thread_id in thread_ids
                    if thread_id in allowed_ids
                ]

        service = DiscoveryService(session=None)  # type: ignore[arg-type]
        trend_service = TrendServiceStub()
        repository = RepositoryStub()
        service.trend_service = trend_service  # type: ignore[assignment]
        service.repo = repository  # type: ignore[assignment]

        result = await service._get_surge_threads_with_retry(
            "reaction",
            days=30,
            limit=2,
            prefs=None,
            channel_ids=[10, 11],
        )

        assert [thread.thread_id for thread in result] == [3, 7]
        assert [call[3] for call in trend_service.calls] == [0, 6]
        assert all(call[4] == [10, 11] for call in trend_service.calls)
        assert all(call[2] == [10, 11] for call in repository.calls)


@pytest.mark.asyncio
class TestGetRandomThreads:
    """随机帖子查询 — func.random()"""

    async def test_get_random_threads_basic(
        self, seeded_discovery_session: AsyncSession
    ):
        """基本随机查询"""
        repo = ThreadRepository(seeded_discovery_session)
        threads = await repo.get_random_threads(
            limit=2,
            channel_ids=[1],
        )
        assert len(threads) == 2
        # 应只从 channel 1 获取
        for t in threads:
            assert t.channel_id == 1
            assert t.show_flag is True
            assert t.not_found_count == 0

    async def test_get_random_threads_exclusion(
        self, seeded_discovery_session: AsyncSession
    ):
        """排除指定频道"""
        repo = ThreadRepository(seeded_discovery_session)
        threads = await repo.get_random_threads(
            limit=10,
            channel_ids=[1, 2],
            exclude_channel_ids=[1],
        )
        # 排除 channel 1 → 只有 channel 2 的帖子
        for t in threads:
            assert t.channel_id == 2

    async def test_get_random_threads_limit(
        self, seeded_discovery_session: AsyncSession
    ):
        """Limit 约束"""
        repo = ThreadRepository(seeded_discovery_session)
        threads = await repo.get_random_threads(
            limit=1,
            channel_ids=[1],
        )
        assert len(threads) == 1

    async def test_get_random_threads_empty_channel(
        self, seeded_discovery_session: AsyncSession
    ):
        """空频道列表 → 空结果"""
        repo = ThreadRepository(seeded_discovery_session)
        threads = await repo.get_random_threads(
            limit=10,
            channel_ids=None,
        )
        # None means all channels — should return all visible threads
        assert len(threads) >= 3
