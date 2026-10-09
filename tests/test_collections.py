"""
收藏仓库集成测试（PostgreSQL 后端）。

覆盖 collections.py API 背后的 CollectionRepository 层：
- add_collection（帖子 → 默认书单；书单 → UserCollection）
- remove_collection（帖子 → 从书单移除；书单 → UserCollection）
- batch add/remove（去重、item_count 维护）
- get_collected_target_ids / get_followed_not_collected_threads

PG 关注点：func.greatest() 防止负数，case() 批量更新，FK-free DELETE，pg_insert
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models import Booklist, Thread, ThreadFollow, UserCollection
from core.collection_repository import CollectionRepository
from shared.enum.collection_type import CollectionType
from shared.time_utils import utc_now


@pytest_asyncio.fixture(scope="function")
async def collection_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供已清理的独立会话。"""
    async with db_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seeded_collection_session(
    collection_session: AsyncSession,
) -> AsyncSession:
    """预填充帖子数据，用于收藏测试。"""
    created_at = datetime(2024, 1, 1)
    threads = [
        Thread(
            channel_id=1,
            thread_id=101,
            title="Collection Thread 1",
            author_id=1,
            created_at=created_at,
            not_found_count=0,
        ),
        Thread(
            channel_id=1,
            thread_id=102,
            title="Collection Thread 2",
            author_id=2,
            created_at=created_at,
            not_found_count=0,
        ),
        Thread(
            channel_id=1,
            thread_id=103,
            title="Collection Thread 3",
            author_id=3,
            created_at=created_at,
            not_found_count=0,
        ),
        Thread(
            channel_id=1,
            thread_id=104,
            title="Followed Thread",
            author_id=4,
            created_at=created_at,
            not_found_count=0,
        ),
    ]
    collection_session.add_all(threads)

    # 预创建书单（用于 BOOKLIST 类型收藏测试）
    booklist = Booklist(
        owner_id=999,
        title="PreExisting Booklist",
        description="For testing",
        is_public=True,
        default_sort_method="join_time",
        default_sort_order="desc",
    )
    collection_session.add(booklist)
    await collection_session.commit()
    return collection_session


@pytest.mark.asyncio
class TestSingleAddCollection:
    """单个收藏添加"""

    async def test_add_thread_collection(self, seeded_collection_session: AsyncSession):
        """帖子收藏 → 自动创建默认书单 + 添加条目"""
        repo = CollectionRepository(seeded_collection_session)
        result = await repo.add_collection(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_id=101,
        )
        assert result is True

        # 验证默认书单已创建
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 1, Booklist.is_default)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.item_count == 1

    async def test_add_thread_collection_duplicate(
        self, seeded_collection_session: AsyncSession
    ):
        """重复收藏同一帖子 → 返回 False"""
        repo = CollectionRepository(seeded_collection_session)
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=101
        )
        result = await repo.add_collection(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_id=101,
        )
        assert result is False

    async def test_add_booklist_collection(
        self, seeded_collection_session: AsyncSession
    ):
        """书单收藏 → UserCollection 表"""
        repo = CollectionRepository(seeded_collection_session)
        # 查找已有的 booklist（预创建在 fixture 中，owner_id=999）
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 999)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.id is not None
        booklist_id = booklist.id

        result = await repo.add_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        assert result is True

        # 验证 UserCollection 记录
        stmt2 = sm_select(UserCollection).where(
            UserCollection.user_id == 1,
            UserCollection.target_type == CollectionType.BOOKLIST.value,
        )  # type: ignore
        r2 = await seeded_collection_session.execute(stmt2)
        coll = r2.scalar_one_or_none()
        assert coll is not None
        assert coll.target_id == booklist_id

    async def test_add_booklist_collection_duplicate(
        self, seeded_collection_session: AsyncSession
    ):
        """重复收藏书单 → 返回 False（IntegrityError 捕获）"""
        repo = CollectionRepository(seeded_collection_session)
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 999)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.id is not None
        booklist_id = booklist.id

        await repo.add_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        result = await repo.add_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        assert result is False


@pytest.mark.asyncio
class TestSingleRemoveCollection:
    """单个收藏移除 — FK-free DELETE, func.greatest()"""

    async def test_remove_thread_collection(
        self, seeded_collection_session: AsyncSession
    ):
        """移除帖子收藏 → BooklistItem 删除 + item_count 扣减"""
        repo = CollectionRepository(seeded_collection_session)
        # 先添加
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=101
        )
        result = await repo.remove_collection(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_id=101,
        )
        assert result is True

        # 验证 item_count 归零
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 1, Booklist.is_default)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.item_count == 0

    async def test_remove_nonexistent_thread(
        self, seeded_collection_session: AsyncSession
    ):
        """移除不存在的帖子收藏 → False"""
        repo = CollectionRepository(seeded_collection_session)
        result = await repo.remove_collection(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_id=101,
        )
        assert result is False

    async def test_remove_booklist_collection(
        self, seeded_collection_session: AsyncSession
    ):
        """移除书单收藏 → UserCollection 记录删除"""
        repo = CollectionRepository(seeded_collection_session)
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 999)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.id is not None
        booklist_id = booklist.id

        await repo.add_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        result = await repo.remove_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        assert result is True

    async def test_remove_nonexistent_booklist(
        self, seeded_collection_session: AsyncSession
    ):
        """移除不存在的书单收藏 → False"""
        repo = CollectionRepository(seeded_collection_session)
        result = await repo.remove_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=99999,
        )
        assert result is False


@pytest.mark.asyncio
class TestBatchRemoveCollections:
    """批量移除 — case() 批量更新, Counter 统计"""

    async def test_batch_remove_threads(self, seeded_collection_session: AsyncSession):
        """批量移除帖子收藏"""
        repo = CollectionRepository(seeded_collection_session)
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=101
        )
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=102
        )

        result = await repo.remove_collections(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_ids=[101, 102],
        )
        assert result.removed_count == 2
        assert result.not_found_count == 0
        assert set(result.removed_ids) == {101, 102}

        # item_count 应扣到 0（使用 func.greatest 不会为负）
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 1, Booklist.is_default)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.item_count == 0

    async def test_batch_remove_partial(self, seeded_collection_session: AsyncSession):
        """部分 ID 不存在 → 正确区分 removed/not_found"""
        repo = CollectionRepository(seeded_collection_session)
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=101
        )

        result = await repo.remove_collections(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_ids=[101, 99999],
        )
        assert result.removed_count == 1
        assert result.not_found_count == 1

    async def test_batch_remove_empty(self, seeded_collection_session: AsyncSession):
        """空列表 → 全零结果"""
        repo = CollectionRepository(seeded_collection_session)
        result = await repo.remove_collections(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_ids=[],
        )
        assert result.removed_count == 0
        assert result.not_found_count == 0

    async def test_batch_remove_booklists(
        self, seeded_collection_session: AsyncSession
    ):
        """批量移除书单收藏"""
        repo = CollectionRepository(seeded_collection_session)
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 999)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.id is not None
        booklist_id = booklist.id

        await repo.add_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        result = await repo.remove_collections(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_ids=[booklist_id],
        )
        assert result.removed_count == 1


@pytest.mark.asyncio
class TestGetCollectedTargetIds:
    """查询收藏状态"""

    async def test_get_collected_thread_ids(
        self, seeded_collection_session: AsyncSession
    ):
        """查询哪些帖子已收藏"""
        repo = CollectionRepository(seeded_collection_session)
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=101
        )
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=102
        )

        collected = await repo.get_collected_target_ids(
            user_id=1,
            target_type=CollectionType.THREAD,
            target_ids=[101, 102, 103],
        )
        assert collected == {101, 102}

    async def test_get_collected_booklist_ids(
        self, seeded_collection_session: AsyncSession
    ):
        """查询哪些书单已收藏"""
        repo = CollectionRepository(seeded_collection_session)
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 999)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.id is not None
        booklist_id = booklist.id

        await repo.add_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        collected = await repo.get_collected_target_ids(
            user_id=1,
            target_type=CollectionType.BOOKLIST,
            target_ids=[booklist_id, 99999],
        )
        assert collected == {booklist_id}

    async def test_no_collected_targets(self, seeded_collection_session: AsyncSession):
        """无收藏的用户 → 空集合"""
        repo = CollectionRepository(seeded_collection_session)
        collected = await repo.get_collected_target_ids(
            user_id=999,
            target_type=CollectionType.THREAD,
            target_ids=[101, 102],
        )
        assert collected == set()

    async def test_empty_target_ids(self, seeded_collection_session: AsyncSession):
        """空 ID 列表 → 空集合"""
        repo = CollectionRepository(seeded_collection_session)
        collected = await repo.get_collected_target_ids(
            user_id=1,
            target_type=CollectionType.THREAD,
            target_ids=[],
        )
        assert collected == set()


@pytest.mark.asyncio
class TestFollowedNotCollected:
    """已关注但未收藏的帖子 — 多表 JOIN"""

    async def test_followed_not_collected(
        self, seeded_collection_session: AsyncSession
    ):
        """关注了但未收藏 → 出现在结果中"""
        repo = CollectionRepository(seeded_collection_session)
        # 添加关注
        follow = ThreadFollow(
            user_id=1,
            thread_id=104,
            followed_at=utc_now(),
            last_viewed_at=None,
        )
        seeded_collection_session.add(follow)
        await seeded_collection_session.commit()

        threads, total = await repo.get_followed_not_collected_threads(
            user_id=1,
            page=1,
            per_page=10,
        )
        assert total == 1
        assert threads[0].thread_id == 104

    async def test_followed_and_collected_excluded(
        self, seeded_collection_session: AsyncSession
    ):
        """关注了且已收藏 → 不在结果中"""
        repo = CollectionRepository(seeded_collection_session)
        follow = ThreadFollow(
            user_id=1,
            thread_id=104,
            followed_at=utc_now(),
            last_viewed_at=None,
        )
        seeded_collection_session.add(follow)
        await seeded_collection_session.commit()
        # 添加收藏
        await repo.add_collection(
            user_id=1, target_type=CollectionType.THREAD.value, target_id=104
        )

        threads, total = await repo.get_followed_not_collected_threads(
            user_id=1,
            page=1,
            per_page=10,
        )
        assert total == 0

    async def test_no_follows(self, seeded_collection_session: AsyncSession):
        """没有关注的用户 → 空列表"""
        repo = CollectionRepository(seeded_collection_session)
        threads, total = await repo.get_followed_not_collected_threads(
            user_id=999,
            page=1,
            per_page=10,
        )
        assert total == 0
        assert threads == []


@pytest.mark.asyncio
class TestGetCollectedTargets:
    """分页获取已收藏目标"""

    async def test_get_collected_threads(self, seeded_collection_session: AsyncSession):
        """Thread 类型 → 通过 BooklistItem 关联，group_by(Thread.id) 去重"""
        repo = CollectionRepository(seeded_collection_session)
        # 将帖子添加到用户收藏（自动创建默认书单 + BooklistItem）
        await repo.add_collection(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_id=101,
        )
        await repo.add_collection(
            user_id=1,
            target_type=CollectionType.THREAD.value,
            target_id=102,
        )

        targets, total = await repo.get_collected_targets(
            user_id=1,
            target_type=CollectionType.THREAD,
            page=1,
            per_page=10,
            model_class=Thread,
        )
        assert total == 2
        target_ids = {t.thread_id for t in targets}
        assert target_ids == {101, 102}

    async def test_get_collected_booklists(
        self, seeded_collection_session: AsyncSession
    ):
        """Booklist 类型 → 通过 UserCollection 关联"""
        repo = CollectionRepository(seeded_collection_session)
        from sqlmodel import select as sm_select

        stmt = sm_select(Booklist).where(Booklist.owner_id == 999)  # type: ignore
        r = await seeded_collection_session.execute(stmt)
        booklist = r.scalar_one_or_none()
        assert booklist is not None
        assert booklist.id is not None
        booklist_id = booklist.id

        await repo.add_collection(
            user_id=1,
            target_type=CollectionType.BOOKLIST.value,
            target_id=booklist_id,
        )
        targets, total = await repo.get_collected_targets(
            user_id=1,
            target_type=CollectionType.BOOKLIST,
            page=1,
            per_page=10,
            model_class=Booklist,
        )
        assert total == 1
        assert targets[0].id == booklist_id

    async def test_get_collected_pagination(
        self, seeded_collection_session: AsyncSession
    ):
        """分页验证 — group_by + offset/limit 正确分页"""
        repo = CollectionRepository(seeded_collection_session)
        # 收藏 3 个帖子
        for tid in [101, 102, 103]:
            await repo.add_collection(
                user_id=1,
                target_type=CollectionType.THREAD.value,
                target_id=tid,
            )

        # 第一页：2 条
        page1, total = await repo.get_collected_targets(
            user_id=1,
            target_type=CollectionType.THREAD,
            page=1,
            per_page=2,
            model_class=Thread,
        )
        assert total == 3
        assert len(page1) == 2

        # 第二页：剩余 1 条
        page2, total2 = await repo.get_collected_targets(
            user_id=1,
            target_type=CollectionType.THREAD,
            page=2,
            per_page=2,
            model_class=Thread,
        )
        assert total2 == 3
        assert len(page2) == 1

        # 两页不应重叠
        page1_ids = {t.thread_id for t in page1}
        page2_ids = {t.thread_id for t in page2}
        assert page1_ids.isdisjoint(page2_ids)
