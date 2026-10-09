"""
标签仓库集成测试（PostgreSQL 后端）。

覆盖 tags.py API 背后的 TagRepository 层：
- get_or_create_tags（批量查询、按需更新和插入）
- get_all_tags / get_tags_for_channels
- update_tag_name
- 跨表聚合查询（Tag → TagBinding → Thread）

PG 关注点：重复同步不消耗序列，缺失实体保留并发冲突保护。
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from models import Tag, Thread, TagBinding, DiscordTagSource
from sqlalchemy import select
from core.discord_tag_sync_service import DiscordTagSyncService
from dto.events.discord_tags_snapshot import DiscordTagsSnapshot
from core.tag_repository import TagRepository
from shared.time_utils import utc_now


@pytest_asyncio.fixture(scope="function")
async def tag_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供已清理的独立会话。"""
    async with db_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def seeded_tag_session(tag_session: AsyncSession) -> AsyncSession:
    """预填充 Tag + Thread + TagBinding 数据。"""
    # 创建线程
    threads = [
        Thread(
            channel_id=1,
            thread_id=101,
            title="Tagged Thread 1",
            author_id=1,
            created_at=utc_now(),
        ),
        Thread(
            channel_id=1,
            thread_id=102,
            title="Tagged Thread 2",
            author_id=1,
            created_at=utc_now(),
        ),
        Thread(
            channel_id=2,
            thread_id=201,
            title="Channel 2 Thread",
            author_id=2,
            created_at=utc_now(),
        ),
        Thread(
            channel_id=1,
            thread_id=103,
            title="No Tags Thread",
            author_id=3,
            created_at=utc_now(),
        ),
    ]
    tag_session.add_all(threads)
    await tag_session.commit()

    # 创建标签
    repo = TagRepository(tag_session)
    await repo.get_or_create_tags(
        {
            10: "百合",
            20: "纯爱",
            30: "后宫",
            40: "异世界",
        }
    )

    # 获取内部 ID → 直接创建 TagBinding（与生产代码一致：TagBinding.target_id = Thread.id）
    for t in threads:
        await tag_session.refresh(t)
    id_map = {t.thread_id: t.id for t in threads}
    sources = list((await tag_session.execute(select(DiscordTagSource))).scalars())
    tag_ids = {t.discord_tag_id: t.tag_id for t in sources}
    source_ids = {t.discord_tag_id: t.id for t in sources}

    links = [
        TagBinding(
            target_type="thread",
            binding_source="discord_sync",
            target_id=id_map[101],
            tag_id=tag_ids[10],
            discord_source_id=source_ids[10],
        ),
        TagBinding(
            target_type="thread",
            binding_source="discord_sync",
            target_id=id_map[101],
            tag_id=tag_ids[20],
            discord_source_id=source_ids[20],
        ),
        TagBinding(
            target_type="thread",
            binding_source="discord_sync",
            target_id=id_map[102],
            tag_id=tag_ids[10],
            discord_source_id=source_ids[10],
        ),
        TagBinding(
            target_type="thread",
            binding_source="discord_sync",
            target_id=id_map[102],
            tag_id=tag_ids[30],
            discord_source_id=source_ids[30],
        ),
        TagBinding(
            target_type="thread",
            binding_source="discord_sync",
            target_id=id_map[201],
            tag_id=tag_ids[40],
            discord_source_id=source_ids[40],
        ),
    ]
    tag_session.add_all(links)
    await tag_session.commit()
    return tag_session


@pytest.mark.asyncio
class TestGetOrCreateTags:
    """INSERT ON CONFLICT DO UPDATE 行为"""

    async def test_create_new_tags(self, tag_session: AsyncSession):
        """批量创建新标签"""
        repo = TagRepository(tag_session)
        tags = await repo.get_or_create_tags({1: "百合", 2: "纯爱"})
        assert len(tags) == 2
        names = {t.name for t in tags}
        ids = set(
            (
                await tag_session.execute(select(DiscordTagSource.discord_tag_id))
            ).scalars()
        )
        assert names == {"百合", "纯爱"}
        assert ids == {1, 2}

    async def test_upsert_updates_existing_name(self, tag_session: AsyncSession):
        """ON CONFLICT 更新已存在标签的名称"""
        repo = TagRepository(tag_session)
        await repo.get_or_create_tags({1: "旧名称"})
        await DiscordTagSyncService(tag_session).apply(
            DiscordTagsSnapshot(1, {1: "新名称"}, utc_now())
        )

        tags = await repo.get_all_tags()
        tag = next(t for t in tags if t.source == "discord")
        assert tag.name == "新名称"

    async def test_empty_tags_data(self, tag_session: AsyncSession):
        """空字典 → 空列表"""
        repo = TagRepository(tag_session)
        tags = await repo.get_or_create_tags({})
        assert tags == []

    async def test_mixed_insert_and_update(self, tag_session: AsyncSession):
        """同时创建新标签和更新已有标签"""
        repo = TagRepository(tag_session)
        await repo.get_or_create_tags({1: "existing"})
        tags = await repo.get_or_create_tags({1: "updated", 2: "new_tag"})
        assert len(tags) == 2
        names = {t.name for t in tags}
        assert names == {"existing", "new_tag"}


@pytest.mark.asyncio
class TestGetTagsForChannels:
    """频道过滤的标签查询 — 直接 SQL join 验证"""

    async def test_get_tags_in_channel_direct(self, seeded_tag_session: AsyncSession):
        """直接 SQL：channel 1 应有 3 个标签"""
        from sqlalchemy import select, func

        stmt = (
            select(func.count(func.distinct(Tag.id)))
            .select_from(Tag)
            .join(TagBinding, Tag.id == TagBinding.tag_id)
            .join(Thread, TagBinding.target_id == Thread.id)
            .where(Thread.channel_id == 1)
        )
        r = await seeded_tag_session.execute(stmt)
        count = r.scalar_one()
        # Channel 1: 百合(101,102), 纯爱(101), 后宫(102) → 3 unique tags
        assert count == 3

    async def test_get_tags_in_channel_2_direct(self, seeded_tag_session: AsyncSession):
        """直接 SQL：channel 2 只有 异世界"""
        from sqlalchemy import select

        stmt = (
            select(Tag.name)
            .select_from(Tag)
            .join(TagBinding, Tag.id == TagBinding.tag_id)
            .join(Thread, TagBinding.target_id == Thread.id)
            .where(Thread.channel_id == 2)
        )
        r = await seeded_tag_session.execute(stmt)
        names = {row[0] for row in r.all()}
        assert names == {"异世界"}

    async def test_get_tags_empty_channels(self, seeded_tag_session: AsyncSession):
        """空频道列表 — 无标签"""
        repo = TagRepository(seeded_tag_session)
        tags = await repo.get_tags_for_channels([])
        assert len(tags) == 0

    async def test_get_tags_nonexistent_channel(self, seeded_tag_session: AsyncSession):
        """不存在的频道 → 空结果"""
        repo = TagRepository(seeded_tag_session)
        tags = await repo.get_tags_for_channels([999])
        assert len(tags) == 0


@pytest.mark.asyncio
class TestGetAllTags:
    """全量标签查询"""

    async def test_get_all_tags_empty(self, tag_session: AsyncSession):
        """空数据库 → 空列表"""
        repo = TagRepository(tag_session)
        tags = await repo.get_all_tags()
        assert list(tags) == []

    async def test_get_all_tags(self, seeded_tag_session: AsyncSession):
        """获取所有标签"""
        repo = TagRepository(seeded_tag_session)
        tags = list(await repo.get_all_tags())
        assert len(tags) == 4
        names = {t.name for t in tags}
        assert names == {"百合", "纯爱", "后宫", "异世界"}

    async def test_get_unique_tags_from_indexed_threads(
        self, seeded_tag_session: AsyncSession
    ):
        """直接 SQL：所有标签都关联了帖子"""
        from sqlalchemy import select, func

        stmt = (
            select(func.count(func.distinct(Tag.id)))
            .select_from(Tag)
            .join(TagBinding, Tag.id == TagBinding.tag_id)
        )
        r = await seeded_tag_session.execute(stmt)
        count = r.scalar_one()
        assert count == 4


@pytest.mark.asyncio
class TestUpdateTagName:
    """标签重命名"""

    async def test_update_existing_tag(self, seeded_tag_session: AsyncSession):
        """更新已存在标签的名称"""
        repo = TagRepository(seeded_tag_session)
        old = Tag(name="自定义", source="custom", category=3)
        seeded_tag_session.add(old)
        await seeded_tag_session.flush()
        await repo.update_tag_name(tag_id=old.id, new_name="百合破坏")

        all_tags = list(await repo.get_all_tags())
        tag = next(t for t in all_tags if t.id == old.id)
        assert tag.name == "百合破坏"

    async def test_update_nonexistent_tag(self, seeded_tag_session: AsyncSession):
        """更新不存在的标签 → 不报错"""
        repo = TagRepository(seeded_tag_session)
        # 不应抛出异常
        await repo.update_tag_name(tag_id=99999, new_name="ghost")


@pytest.mark.asyncio
class TestCrossTableAggregation:
    """跨表聚合查询 — Tag → TagBinding → Thread"""

    async def test_aggregate_tag_thread_count(self, seeded_tag_session: AsyncSession):
        """按标签聚合帖子数"""
        from sqlalchemy import func, select

        stmt = (
            select(
                Tag.name,
                func.count(func.distinct(Thread.id)),
            )
            .select_from(Tag)
            .join(TagBinding, Tag.id == TagBinding.tag_id)
            .join(Thread, TagBinding.target_id == Thread.id)
            .group_by(Tag.name)
        )
        result = await seeded_tag_session.execute(stmt)
        rows = list(result.all())

        # 百合: thread 101 + 102 → 2
        # 纯爱: thread 101 → 1
        # 后宫: thread 102 → 1
        # 异世界: thread 201 → 1
        tag_counts = {str(row[0]): int(row[1]) for row in rows}
        assert tag_counts["百合"] == 2
        assert tag_counts["纯爱"] == 1
        assert tag_counts["后宫"] == 1
        assert tag_counts["异世界"] == 1


@pytest.mark.asyncio
async def test_existing_sync_does_not_consume_tag_ids(tag_session: AsyncSession):
    """重复同步仅查询已有实体，只有新概念消耗标准标签序列。"""
    repo = TagRepository(tag_session)
    initial = await repo.get_or_create_tags({101: "原名", 102: "另一个"})
    original_ids = {tag.id for tag in initial}
    for _ in range(3):
        unchanged = await repo.get_or_create_tags({101: "缓存旧名", 102: "另一个"})
        assert {tag.id for tag in unchanged} == original_ids
        assert {tag.name for tag in unchanged} == {"原名", "另一个"}
    mixed = await repo.get_or_create_tags({101: "缓存旧名", 103: "新增"})
    new_tag = next(tag for tag in mixed if tag.name == "新增")
    assert new_tag.id == max(original_ids) + 1
