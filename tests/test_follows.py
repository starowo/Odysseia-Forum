"""
关注仓库集成测试（PostgreSQL 后端）。

覆盖 follows.py API 背后的 ThreadFollowRepository 层：
- add_follow / batch_add_follows
- remove_follow
- update_last_viewed（单个 + 全部）
- get_user_follows / get_unread_count / is_following

PG 关注点：datetime naive 比较（followed_at, last_viewed_at），FK-free DELETE
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from shared.time_utils import utc_now

from models import Thread
from core.follow_repository import ThreadFollowRepository


@pytest_asyncio.fixture(scope="function")
async def follow_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供已清理的独立会话。"""
    async with db_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seeded_follow_session(
    follow_session: AsyncSession,
) -> AsyncSession:
    """预填充帖子数据的会话。"""
    threads = [
        Thread(
            channel_id=1,
            thread_id=101,
            title="Follow Thread 1",
            author_id=1,
            created_at=utc_now(),
        ),
        Thread(
            channel_id=1,
            thread_id=102,
            title="Follow Thread 2",
            author_id=2,
            created_at=utc_now(),
            latest_update_at=utc_now(),
        ),
        Thread(
            channel_id=1,
            thread_id=103,
            title="Follow Thread 3",
            author_id=3,
            created_at=utc_now(),
        ),
    ]
    follow_session.add_all(threads)
    await follow_session.commit()
    return follow_session


@pytest.mark.asyncio
class TestAddFollow:
    """添加关注"""

    async def test_add_new_follow(self, seeded_follow_session: AsyncSession):
        """新关注 → 返回 True"""
        repo = ThreadFollowRepository(seeded_follow_session)
        result = await repo.add_follow(user_id=1, thread_id=101)
        assert result is True

    async def test_duplicate_follow_idempotent(
        self, seeded_follow_session: AsyncSession
    ):
        """重复关注幂等 → 返回 False，不报错"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        result = await repo.add_follow(user_id=1, thread_id=101)
        assert result is False

    async def test_add_follow_with_auto_view(self, seeded_follow_session: AsyncSession):
        """auto_view=True → last_viewed_at 被设置"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101, auto_view=True)
        assert await repo.is_following(1, 101)
        # 通过 get_user_follows 验证 last_viewed_at 不为 None
        follows, _ = await repo.get_user_follows(user_id=1)
        assert len(follows) == 1
        assert follows[0].last_viewed_at is not None

    async def test_add_follow_without_auto_view(
        self, seeded_follow_session: AsyncSession
    ):
        """auto_view=False（默认）→ last_viewed_at 为 None"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101, auto_view=False)
        follows, _ = await repo.get_user_follows(user_id=1)
        assert len(follows) == 1
        assert follows[0].last_viewed_at is None


@pytest.mark.asyncio
class TestBatchAddFollows:
    """批量添加关注"""

    async def test_batch_add_all_new(self, seeded_follow_session: AsyncSession):
        """全部新用户 → 返回添加数量"""
        repo = ThreadFollowRepository(seeded_follow_session)
        count = await repo.batch_add_follows(thread_id=101, user_ids=[10, 20, 30])
        assert count == 3
        for uid in [10, 20, 30]:
            assert await repo.is_following(uid, 101)

    async def test_batch_add_partial_existing(
        self, seeded_follow_session: AsyncSession
    ):
        """部分已存在 → 只计算新增"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=10, thread_id=101)
        count = await repo.batch_add_follows(thread_id=101, user_ids=[10, 20, 30])
        assert count == 2  # 20, 30 是新的

    async def test_batch_add_empty_list(self, seeded_follow_session: AsyncSession):
        """空用户列表 → 返回 0"""
        repo = ThreadFollowRepository(seeded_follow_session)
        count = await repo.batch_add_follows(thread_id=101, user_ids=[])
        assert count == 0


@pytest.mark.asyncio
class TestRemoveFollow:
    """取消关注 — FK-free DELETE"""

    async def test_remove_existing(self, seeded_follow_session: AsyncSession):
        """取消已存在的关注 → True"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        result = await repo.remove_follow(user_id=1, thread_id=101)
        assert result is True
        assert not await repo.is_following(1, 101)

    async def test_remove_nonexistent(self, seeded_follow_session: AsyncSession):
        """取消不存在的关注 → False"""
        repo = ThreadFollowRepository(seeded_follow_session)
        result = await repo.remove_follow(user_id=1, thread_id=101)
        assert result is False


@pytest.mark.asyncio
class TestLastViewed:
    """更新已读时间 — datetime naive 比较"""

    async def test_update_last_viewed_single(self, seeded_follow_session: AsyncSession):
        """更新单个帖子的已读时间"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        result = await repo.update_last_viewed(user_id=1, thread_id=101)
        assert result is True
        follows, _ = await repo.get_user_follows(user_id=1)
        assert follows[0].last_viewed_at is not None

    async def test_update_last_viewed_all(self, seeded_follow_session: AsyncSession):
        """更新所有关注的已读时间"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.add_follow(user_id=1, thread_id=102)
        result = await repo.update_last_viewed(user_id=1, thread_id=None)
        assert result is True
        follows, _ = await repo.get_user_follows(user_id=1)
        for f in follows:
            assert f.last_viewed_at is not None

    async def test_update_last_viewed_nonexistent(
        self, seeded_follow_session: AsyncSession
    ):
        """更新未关注帖子的已读时间 → False"""
        repo = ThreadFollowRepository(seeded_follow_session)
        result = await repo.update_last_viewed(user_id=1, thread_id=101)
        assert result is False


@pytest.mark.asyncio
class TestGetFollows:
    """获取关注列表"""

    async def test_get_empty_follows(self, seeded_follow_session: AsyncSession):
        """无关注的用户 → 空列表"""
        repo = ThreadFollowRepository(seeded_follow_session)
        follows, total = await repo.get_user_follows(user_id=999)
        assert total == 0
        assert follows == []

    async def test_get_follows_with_data(self, seeded_follow_session: AsyncSession):
        """有关注的用户 → 返回帖子详情"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.add_follow(user_id=1, thread_id=102)

        follows, total = await repo.get_user_follows(user_id=1)
        assert total == 2
        assert len(follows) == 2
        # 验证字段结构
        for f in follows:
            assert hasattr(f, "thread_id")
            assert hasattr(f, "title")
            assert hasattr(f, "followed_at")
            assert hasattr(f, "last_viewed_at")
            assert hasattr(f, "has_update")

    async def test_get_follows_pagination(self, seeded_follow_session: AsyncSession):
        """分页验证"""
        repo = ThreadFollowRepository(seeded_follow_session)
        for tid in [101, 102, 103]:
            await repo.add_follow(user_id=1, thread_id=tid)

        page1, total = await repo.get_user_follows(user_id=1, limit=2, offset=0)
        assert len(page1) == 2
        assert total == 3

        page2, _ = await repo.get_user_follows(user_id=1, limit=2, offset=2)
        assert len(page2) == 1


@pytest.mark.asyncio
class TestUnreadCount:
    """未读计数"""

    async def test_unread_count_zero_when_no_follows(
        self, seeded_follow_session: AsyncSession
    ):
        """无关注 → 未读计数 0"""
        repo = ThreadFollowRepository(seeded_follow_session)
        count = await repo.get_unread_count(user_id=999)
        assert count == 0

    async def test_unread_count_with_update(self, seeded_follow_session: AsyncSession):
        """有更新且未查看 → 计数正确"""
        repo = ThreadFollowRepository(seeded_follow_session)
        # 关注 thread 102（有 latest_update_at）
        await repo.add_follow(user_id=1, thread_id=102)
        count = await repo.get_unread_count(user_id=1)
        # 未查看 + 有更新 = 1 未读
        assert count == 1

    async def test_unread_count_after_viewed(self, seeded_follow_session: AsyncSession):
        """已查看后 → 未读计数归零"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=102)
        await repo.update_last_viewed(user_id=1, thread_id=102)
        count = await repo.get_unread_count(user_id=1)
        assert count == 0


@pytest.mark.asyncio
class TestIsFollowing:
    """关注状态检查"""

    async def test_is_following_true(self, seeded_follow_session: AsyncSession):
        """已关注 → True"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        assert await repo.is_following(1, 101)

    async def test_is_following_false(self, seeded_follow_session: AsyncSession):
        """未关注 → False"""
        repo = ThreadFollowRepository(seeded_follow_session)
        assert not await repo.is_following(1, 101)

    async def test_is_following_inactive_not_counted(
        self, seeded_follow_session: AsyncSession
    ):
        """非活跃关注 → active_only=True 时返回 False"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.batch_mark_inactive(thread_id=101, user_ids=[1])
        # active_only=True（默认）
        assert not await repo.is_following(1, 101)
        # active_only=False 可以查到
        assert await repo.is_following(1, 101, active_only=False)


@pytest.mark.asyncio
class TestMarkInactive:
    """批量标记非活跃"""

    async def test_mark_inactive(self, seeded_follow_session: AsyncSession):
        """正常标记 → 返回受影响行数"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.add_follow(user_id=2, thread_id=101)
        count = await repo.batch_mark_inactive(thread_id=101, user_ids=[1, 2])
        assert count == 2
        # 确认已是非活跃
        assert not await repo.is_following(1, 101)
        assert not await repo.is_following(2, 101)

    async def test_mark_inactive_empty_list(self, seeded_follow_session: AsyncSession):
        """空列表 → 返回 0"""
        repo = ThreadFollowRepository(seeded_follow_session)
        count = await repo.batch_mark_inactive(thread_id=101, user_ids=[])
        assert count == 0

    async def test_mark_inactive_already_inactive(
        self, seeded_follow_session: AsyncSession
    ):
        """已是非活跃 → 幂等，返回 0"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.batch_mark_inactive(thread_id=101, user_ids=[1])
        # 再次标记应返回 0
        count = await repo.batch_mark_inactive(thread_id=101, user_ids=[1])
        assert count == 0

    async def test_mark_inactive_partial(self, seeded_follow_session: AsyncSession):
        """部分活跃部分不活跃 → 只计活跃的"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.add_follow(user_id=2, thread_id=101)
        # 先标记 user 1 为非活跃
        await repo.batch_mark_inactive(thread_id=101, user_ids=[1])
        # 再批量标记 [1, 2]，应只影响 user 2
        count = await repo.batch_mark_inactive(thread_id=101, user_ids=[1, 2])
        assert count == 1


@pytest.mark.asyncio
class TestReactivateFollow:
    """重新激活非活跃关注"""

    async def test_reactivate_inactive(self, seeded_follow_session: AsyncSession):
        """非活跃记录 → add_follow 重新激活，返回 True"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.batch_mark_inactive(thread_id=101, user_ids=[1])
        # 重新关注应激活
        result = await repo.add_follow(user_id=1, thread_id=101)
        assert result is True
        assert await repo.is_following(1, 101)

    async def test_reactivate_active_noop(self, seeded_follow_session: AsyncSession):
        """活跃记录 → add_follow 幂等，返回 False"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        result = await repo.add_follow(user_id=1, thread_id=101)
        assert result is False


@pytest.mark.asyncio
class TestGetFollowsActiveFilter:
    """active_flag 筛选"""

    async def test_filter_active(self, seeded_follow_session: AsyncSession):
        """active_flag=True → 仅活跃"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.add_follow(user_id=1, thread_id=102)
        await repo.batch_mark_inactive(thread_id=102, user_ids=[1])

        follows, total = await repo.get_user_follows(user_id=1, active_flag=True)
        assert total == 1
        assert follows[0].thread_id == 101

    async def test_filter_inactive(self, seeded_follow_session: AsyncSession):
        """active_flag=False → 仅过去关注"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.add_follow(user_id=1, thread_id=102)
        await repo.batch_mark_inactive(thread_id=102, user_ids=[1])

        follows, total = await repo.get_user_follows(user_id=1, active_flag=False)
        assert total == 1
        assert follows[0].thread_id == 102

    async def test_filter_all(self, seeded_follow_session: AsyncSession):
        """active_flag=None → 全部"""
        repo = ThreadFollowRepository(seeded_follow_session)
        await repo.add_follow(user_id=1, thread_id=101)
        await repo.add_follow(user_id=1, thread_id=102)
        await repo.batch_mark_inactive(thread_id=102, user_ids=[1])

        follows, total = await repo.get_user_follows(user_id=1, active_flag=None)
        assert total == 2
