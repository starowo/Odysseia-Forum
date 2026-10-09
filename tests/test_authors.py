"""
作者仓库集成测试（PostgreSQL 后端）。

覆盖 authors.py API 背后的 AuthorRepository 层：
- upsert_author（INSERT ON CONFLICT DO UPDATE）
- get_author / get_authors_by_ids
- get_author_stats（聚合 Thread 表统计）
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from shared.time_utils import utc_now

from models import Thread
from core.author_repository import AuthorRepository


@pytest_asyncio.fixture(scope="function")
async def author_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供已清理的独立会话。"""
    async with db_session_factory() as session:
        yield session


@pytest.mark.asyncio
class TestAuthorUpsert:
    """INSERT ON CONFLICT DO UPDATE 行为验证"""

    async def test_upsert_new_author(self, author_session: AsyncSession):
        """创建新作者 → 字段正确写入"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 1001,
                "name": "TestUser",
                "global_name": "GlobalTest",
                "display_name": "DisplayTest",
                "avatar_url": "https://example.com/avatar.png",
                "last_updated": utc_now(),
            }
        )

        author = await repo.get_author(1001)
        assert author is not None
        assert author.name == "TestUser"
        assert author.global_name == "GlobalTest"
        assert author.display_name == "DisplayTest"
        assert author.avatar_url == "https://example.com/avatar.png"

    async def test_upsert_updates_existing_author(self, author_session: AsyncSession):
        """重复 upsert → ON CONFLICT 更新而非报错"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 1002,
                "name": "OldName",
                "global_name": None,
                "display_name": "OldDisplay",
                "avatar_url": None,
                "last_updated": utc_now(),
            }
        )
        await repo.upsert_author(
            {
                "id": 1002,
                "name": "NewName",
                "global_name": "NewGlobal",
                "display_name": "NewDisplay",
                "avatar_url": None,
                "last_updated": utc_now(),
            }
        )

        author = await repo.get_author(1002)
        assert author is not None
        assert author.name == "NewName"
        assert author.global_name == "NewGlobal"

    async def test_upsert_minimal_fields(self, author_session: AsyncSession):
        """只提供必要字段的 upsert"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 1003,
                "name": "Minimal",
                "display_name": "MinDisp",
                "last_updated": utc_now(),
            }
        )

        author = await repo.get_author(1003)
        assert author is not None
        assert author.name == "Minimal"
        assert author.global_name is None


@pytest.mark.asyncio
class TestAuthorQuery:
    """查询方法验证"""

    async def test_get_author_exists(self, author_session: AsyncSession):
        """获取存在的作者"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 2001,
                "name": "QueryTest",
                "display_name": "QDisp",
                "last_updated": utc_now(),
            }
        )

        author = await repo.get_author(2001)
        assert author is not None
        assert author.id == 2001

    async def test_get_author_not_found(self, author_session: AsyncSession):
        """获取不存在的作者 → None"""
        repo = AuthorRepository(author_session)
        author = await repo.get_author(99999)
        assert author is None

    async def test_get_authors_by_ids(self, author_session: AsyncSession):
        """批量获取 → 按 ID 列表返回"""
        repo = AuthorRepository(author_session)
        for i in range(5):
            await repo.upsert_author(
                {
                    "id": 3001 + i,
                    "name": f"BatchUser{i}",
                    "display_name": f"BD{i}",
                    "last_updated": utc_now(),
                }
            )

        authors = await repo.get_authors_by_ids([3001, 3003, 3005])
        assert len(authors) == 3
        ids = {a.id for a in authors}
        assert ids == {3001, 3003, 3005}

    async def test_get_authors_by_ids_empty(self, author_session: AsyncSession):
        """空 ID 列表 → 空列表"""
        repo = AuthorRepository(author_session)
        authors = await repo.get_authors_by_ids([])
        assert authors == []

    async def test_get_authors_by_ids_partial(self, author_session: AsyncSession):
        """部分 ID 不存在 → 只返回存在的"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 4001,
                "name": "Partial",
                "display_name": "PDisp",
                "last_updated": utc_now(),
            }
        )

        authors = await repo.get_authors_by_ids([4001, 99999])
        assert len(authors) == 1
        assert authors[0].id == 4001


@pytest.mark.asyncio
class TestAuthorStats:
    """作者统计聚合验证 — func.count / func.coalesce / func.sum"""

    async def test_stats_no_threads(self, author_session: AsyncSession):
        """无帖子的作者 → 统计全为 0"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 5001,
                "name": "NoThreads",
                "display_name": "NTDisp",
                "last_updated": utc_now(),
            }
        )

        stats = await repo.get_author_stats(5001)
        assert stats["thread_count"] == 0
        assert stats["reaction_count"] == 0
        assert stats["reply_count"] == 0

    async def test_stats_with_threads(self, author_session: AsyncSession):
        """有帖子的作者 → 正确聚合"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 5002,
                "name": "WithThreads",
                "display_name": "WTDisp",
                "last_updated": utc_now(),
            }
        )

        # 添加帖子
        threads = [
            Thread(
                channel_id=1,
                thread_id=10001,
                title="Post 1",
                author_id=5002,
                created_at=utc_now(),
                reaction_count=5,
                reply_count=3,
                not_found_count=0,
            ),
            Thread(
                channel_id=1,
                thread_id=10002,
                title="Post 2",
                author_id=5002,
                created_at=utc_now(),
                reaction_count=10,
                reply_count=7,
                not_found_count=0,
            ),
        ]
        author_session.add_all(threads)
        await author_session.commit()

        stats = await repo.get_author_stats(5002)
        assert stats["thread_count"] == 2
        assert stats["reaction_count"] == 15  # 5 + 10
        assert stats["reply_count"] == 10  # 3 + 7

    async def test_stats_excludes_soft_deleted(self, author_session: AsyncSession):
        """not_found_count > 0 的帖子不计入统计"""
        repo = AuthorRepository(author_session)
        await repo.upsert_author(
            {
                "id": 5003,
                "name": "SoftDeleted",
                "display_name": "SDDisp",
                "last_updated": utc_now(),
            }
        )

        threads = [
            Thread(
                channel_id=1,
                thread_id=10011,
                title="Active",
                author_id=5003,
                created_at=utc_now(),
                reaction_count=5,
                reply_count=2,
                not_found_count=0,
            ),
            Thread(
                channel_id=1,
                thread_id=10012,
                title="SoftDeleted",
                author_id=5003,
                created_at=utc_now(),
                reaction_count=100,
                reply_count=50,
                not_found_count=1,
            ),
        ]
        author_session.add_all(threads)
        await author_session.commit()

        stats = await repo.get_author_stats(5003)
        assert stats["thread_count"] == 1
        assert stats["reaction_count"] == 5
        assert stats["reply_count"] == 2

    async def test_stats_nonexistent_author(self, author_session: AsyncSession):
        """不存在的作者 → 全 0"""
        repo = AuthorRepository(author_session)
        stats = await repo.get_author_stats(99999)
        assert stats["thread_count"] == 0
