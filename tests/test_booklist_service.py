import pytest
import pytest_asyncio
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlmodel import delete, select

from models import Booklist
from models import BooklistItem
from models import Thread
from models import Author
from models import TagBinding
from models import ThreadFollow
from booklist.booklist_service import BooklistService
from core.booklist_repository import BooklistRepository
from core.booklist_item_repository import BooklistItemRepository
from shared.time_utils import utc_now
from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData


# ============================================================
# 测试数据 Fixture
# ============================================================


@pytest_asyncio.fixture(scope="function")
async def seeded_db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    提供一个填充了测试数据的数据库会话。
    """
    async with db_session_factory() as session:
        # 创建作者
        author = Author(
            id=1,
            name="TestAuthor",
            global_name="GlobalTest",
            display_name="DisplayTest",
            avatar_url="https://example.com/avatar.png",
        )
        session.add(author)
        # 创建帖子
        threads = [
            Thread(
                channel_id=100,
                thread_id=1001,
                title="Test Thread 1",
                author_id=1,
                created_at=utc_now(),
                reaction_count=5,
                reply_count=2,
            ),
            Thread(
                channel_id=100,
                thread_id=1002,
                title="Test Thread 2",
                author_id=1,
                created_at=utc_now(),
                reaction_count=10,
                reply_count=3,
            ),
        ]
        session.add_all(threads)
        await session.commit()

        yield session

        # 在每个测试结束后清理数据
        await session.execute(delete(BooklistItem))
        await session.execute(delete(Booklist))
        await session.execute(delete(TagBinding))
        await session.execute(delete(ThreadFollow))
        await session.execute(delete(Thread))
        await session.execute(delete(Author))
        await session.commit()


SORT_THREAD_SPECS = [
    # (thread_id, title, created_at_days_ago, reaction_count, reply_count, collection_count, last_active_days_ago)
    (3001, "A", 30, 5, 1, 0, 20),
    (3002, "B", 14, 20, 3, 2, 10),
    (3003, "C", 7, 1, 10, 5, 5),
    (3004, "D", 1, 100, 0, 10, 1),
    (3005, "E", 0, 50, 5, 1, 0),
]


@pytest_asyncio.fixture(scope="function")
async def seeded_sort_data(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供包含 5 个属性各异的帖子的数据库会话，专用于排序测试。"""
    from datetime import timedelta

    async with db_session_factory() as session:
        author = Author(
            id=10,
            name="SortAuthor",
            global_name="SortGlobal",
            display_name="SortDisplay",
            avatar_url="https://example.com/avatar.png",
        )
        session.add(author)

        now = utc_now()
        threads = []
        for tid, title, days_ago, rc, rpc, cc, la_days in SORT_THREAD_SPECS:
            threads.append(
                Thread(
                    channel_id=200,
                    thread_id=tid,
                    title=title,
                    author_id=10,
                    created_at=now - timedelta(days=days_ago),
                    reaction_count=rc,
                    reply_count=rpc,
                    collection_count=cc,
                    last_active_at=now - timedelta(days=la_days),
                )
            )
        session.add_all(threads)
        await session.commit()

        yield session

        await session.execute(delete(BooklistItem))
        await session.execute(delete(Booklist))
        await session.execute(delete(TagBinding))
        await session.execute(delete(ThreadFollow))
        await session.execute(delete(Thread))
        await session.execute(delete(Author))
        await session.commit()


# ============================================================
# 书单 CRUD 测试
# ============================================================


@pytest.mark.asyncio
async def test_create_booklist(seeded_db_session: AsyncSession):
    """测试创建书单"""
    service = BooklistRepository(seeded_db_session)
    booklist = await service.create_booklist(
        owner_id=123,
        title="My Booklist",
        description="A test booklist",
        cover_image_url="https://example.com/cover.jpg",
        is_public=True,
        default_sort_method="join_time",
        default_sort_order="desc",
    )
    assert booklist.id is not None
    assert booklist.title == "My Booklist"
    assert booklist.owner_id == 123
    assert booklist.item_count == 0
    assert booklist.collection_count == 0
    assert booklist.view_count == 0


@pytest.mark.asyncio
async def test_get_booklist(seeded_db_session: AsyncSession):
    """测试获取书单"""
    service = BooklistRepository(seeded_db_session)
    created = await service.create_booklist(
        owner_id=456, title="Get Test", description="Test"
    )
    assert created.id is not None
    fetched = await service.get_booklist(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == "Get Test"


@pytest.mark.asyncio
async def test_update_booklist(seeded_db_session: AsyncSession):
    """测试更新书单"""
    service = BooklistRepository(seeded_db_session)
    created = await service.create_booklist(
        owner_id=789, title="Original", description="Old"
    )
    assert created.id is not None
    updated = await service.update_booklist(
        booklist_id=created.id,
        title="Updated",
        description="New",
        is_public=False,
        default_sort_method="display_order",
        default_sort_order="asc",
    )
    assert updated is not None
    assert updated.title == "Updated"
    assert updated.description == "New"
    assert updated.is_public is False
    assert updated.default_sort_method == "display_order"
    assert updated.default_sort_order == "asc"


@pytest.mark.asyncio
async def test_delete_booklist(seeded_db_session: AsyncSession):
    """测试删除书单"""
    service = BooklistRepository(seeded_db_session)
    created = await service.create_booklist(
        owner_id=999, title="To Delete", description="Will be deleted"
    )
    assert created.id is not None
    success = await service.delete_booklist(created.id)
    assert success is True
    fetched = await service.get_booklist(created.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_add_thread_to_booklist(seeded_db_session: AsyncSession):
    """测试向书单添加帖子"""
    service = BooklistRepository(seeded_db_session)
    booklist = await service.create_booklist(owner_id=111, title="Add Test")
    assert booklist.id is not None
    booklist_id = booklist.id
    # 添加第一个帖子
    items = await service.add_threads_to_booklist(
        booklist_id=booklist_id,
        items=[
            BooklistItemAddData(thread_id=1001, comment="Great thread", display_order=1)
        ],
    )
    assert len(items) == 1
    item1 = items[0]
    assert item1.id is not None
    assert item1.thread_id == 1001
    assert item1.comment == "Great thread"
    assert item1.display_order == 1
    # 书单的 item_count 应增加
    updated_booklist = await service.get_booklist(booklist_id)
    assert updated_booklist is not None
    assert updated_booklist.item_count == 1
    # 添加第二个帖子，不指定 display_order，应自动递增
    items2 = await service.add_threads_to_booklist(
        booklist_id=booklist_id,
        items=[BooklistItemAddData(thread_id=1002, comment="Another thread")],
    )
    assert items2[0].display_order == 2
    updated_booklist = await service.get_booklist(booklist_id)
    assert updated_booklist is not None
    assert updated_booklist.item_count == 2


@pytest.mark.asyncio
async def test_remove_thread_from_booklist(seeded_db_session: AsyncSession):
    """测试从书单移除帖子"""
    service = BooklistRepository(seeded_db_session)
    booklist = await service.create_booklist(owner_id=222, title="Remove Test")
    assert booklist.id is not None
    booklist_id = booklist.id
    await service.add_threads_to_booklist(
        booklist_id, items=[BooklistItemAddData(thread_id=1001)]
    )
    # 移除存在的帖子
    deleted = await service.remove_threads_from_booklist(booklist_id, [1001])
    assert deleted == 1
    updated_booklist = await service.get_booklist(booklist_id)
    assert updated_booklist is not None
    assert updated_booklist.item_count == 0
    # 移除不存在的帖子
    deleted = await service.remove_threads_from_booklist(booklist_id, [9999])
    assert deleted == 0


@pytest.mark.asyncio
async def test_list_booklists(seeded_db_session: AsyncSession):
    """测试列出书单"""
    service = BooklistRepository(seeded_db_session)
    # 创建多个书单
    for i in range(5):
        await service.create_booklist(
            owner_id=333,
            title=f"Booklist {i}",
            is_public=(i % 2 == 0),
        )
    # 列出所有书单
    booklists, total = await service.list_booklists(owner_id=333, limit=10, offset=0)
    assert total == 5
    assert len(booklists) == 5
    # 过滤公开书单
    public, total_public = await service.list_booklists(
        owner_id=333, is_public=True, limit=10, offset=0
    )
    assert total_public == 3  # 0,2,4 是公开的
    # 分页测试
    page1, total1 = await service.list_booklists(owner_id=333, limit=2, offset=0)
    assert len(page1) == 2
    assert total1 == 5


# ============================================================
# 书单帖子排序测试
# ============================================================


@pytest.mark.asyncio
async def test_get_booklist_items(seeded_db_session: AsyncSession):
    """测试获取书单内容 —— 默认 join_time desc 排序 + 分页"""
    service = BooklistRepository(seeded_db_session)
    booklist = await service.create_booklist(owner_id=444, title="Items Test")
    assert booklist.id is not None
    booklist_id = booklist.id
    await service.add_threads_to_booklist(
        booklist_id,
        items=[
            BooklistItemAddData(thread_id=1001, comment="First"),
            BooklistItemAddData(thread_id=1002, comment="Second"),
        ],
    )
    item_service = BooklistItemRepository(seeded_db_session)
    items, total = await item_service.get_booklist_items_with_details(
        booklist_id,
        default_sort_method="join_time",
        default_sort_order="desc",
        limit=10,
        offset=0,
    )
    assert total == 2
    assert len(items) == 2
    # join_time desc = BooklistItem.created_at DESC，后添加的 thread 1002 排前面
    first = items[0]
    assert first.thread_id == 1002
    assert first.comment == "Second"
    assert first.title is not None
    assert first.author is not None
    # 分页测试
    items_page1, total_page1 = await item_service.get_booklist_items_with_details(
        booklist_id,
        default_sort_method="join_time",
        default_sort_order="desc",
        limit=1,
        offset=0,
    )
    assert len(items_page1) == 1
    assert total_page1 == 2


@pytest.mark.asyncio
async def test_get_booklist_items_sort_hot(seeded_sort_data: AsyncSession):
    """hot 排序 = Reddit Hot: log10(reactions) + epoch / time_decay，新 + 高反应排前面"""
    service = BooklistRepository(seeded_sort_data)
    booklist = await service.create_booklist(owner_id=445, title="Hot Sort")
    assert booklist.id is not None
    booklist_id = booklist.id

    await service.add_threads_to_booklist(
        booklist_id,
        items=[
            BooklistItemAddData(thread_id=tid) for tid in (3001, 3002, 3003, 3004, 3005)
        ],
    )

    item_service = BooklistItemRepository(seeded_sort_data)
    items, total = await item_service.get_booklist_items_with_details(
        booklist_id,
        default_sort_method="hot",
        default_sort_order="desc",
        limit=10,
        offset=0,
    )
    assert total == 5
    # Reddit Hot = log10(reactions) + epoch / time_decay
    # D(reaction=100, 1d前) ≈ 1.995   E(reaction=50, 今天)  ≈ 1.697
    # C(reaction=1,  7d前)  ≈ −0.672  B(reaction=20, 14d前) ≈ −0.043
    # A(reaction=5,  30d前) ≈ −2.181
    expected = [3004, 3005, 3003, 3002, 3001]
    assert [it.thread_id for it in items] == expected


# ---- 参数化：各排序方法验证实际顺序 ----

SORT_ORDER_SPECS = [
    # (method, order, attr_name, expected_tids_ascending)
    ("created_at", "asc", "created_at", [3001, 3002, 3003, 3004, 3005]),
    ("created_at", "desc", "created_at", [3005, 3004, 3003, 3002, 3001]),
    ("reaction_count", "asc", "reaction_count", [3003, 3001, 3002, 3005, 3004]),
    ("reaction_count", "desc", "reaction_count", [3004, 3005, 3002, 3001, 3003]),
    ("reply_count", "asc", "reply_count", [3004, 3001, 3002, 3005, 3003]),
    ("reply_count", "desc", "reply_count", [3003, 3005, 3002, 3001, 3004]),
    ("collection_count", "asc", "collection_count", [3001, 3005, 3002, 3003, 3004]),
    ("collection_count", "desc", "collection_count", [3004, 3003, 3002, 3005, 3001]),
    ("last_active_at", "desc", "last_active_at", [3005, 3004, 3003, 3002, 3001]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method, order, attr, expected", SORT_ORDER_SPECS)
async def test_get_booklist_items_sort_order(
    seeded_sort_data: AsyncSession,
    method: str,
    order: str,
    attr: str,
    expected: list[int],
):
    """验证每种排序方法的结果顺序正确"""
    service = BooklistRepository(seeded_sort_data)
    booklist = await service.create_booklist(
        owner_id=446, title=f"Sort {method} {order}"
    )
    assert booklist.id is not None
    booklist_id = booklist.id

    await service.add_threads_to_booklist(
        booklist_id,
        items=[
            BooklistItemAddData(thread_id=tid) for tid in (3001, 3002, 3003, 3004, 3005)
        ],
    )

    item_service = BooklistItemRepository(seeded_sort_data)
    items, total = await item_service.get_booklist_items_with_details(
        booklist_id,
        default_sort_method=method,
        default_sort_order=order,
        limit=10,
        offset=0,
    )
    assert total == 5
    assert [it.thread_id for it in items] == expected


@pytest.mark.asyncio
async def test_get_booklist_items_sort_display_order(seeded_sort_data: AsyncSession):
    """display_order 排序：按作者自定义顺序"""
    service = BooklistRepository(seeded_sort_data)
    booklist = await service.create_booklist(owner_id=447, title="DispOrder")
    assert booklist.id is not None
    booklist_id = booklist.id

    orders = [30, 20, 50, 10, 40]
    await service.add_threads_to_booklist(
        booklist_id,
        items=[
            BooklistItemAddData(thread_id=3001 + i, display_order=orders[i])
            for i in range(5)
        ],
    )

    item_service = BooklistItemRepository(seeded_sort_data)
    items, _ = await item_service.get_booklist_items_with_details(
        booklist_id,
        default_sort_method="display_order",
        default_sort_order="asc",
        limit=10,
        offset=0,
    )
    assert [it.display_order for it in items] == sorted(orders)


# ============================================================
# 书单统计测试
# ============================================================


@pytest.mark.asyncio
async def test_increment_view_count(seeded_db_session: AsyncSession):
    """测试增加查看次数"""
    service = BooklistRepository(seeded_db_session)
    booklist = await service.create_booklist(owner_id=555, title="View Test")
    assert booklist.id is not None
    booklist_id = booklist.id
    assert booklist.view_count == 0
    await service.increment_view_count(booklist_id)
    updated = await service.get_booklist(booklist_id)
    assert updated is not None
    assert updated.view_count == 1


@pytest.mark.asyncio
async def test_update_collection_count(seeded_db_session: AsyncSession):
    """测试更新收藏次数"""
    service = BooklistRepository(seeded_db_session)
    booklist = await service.create_booklist(owner_id=666, title="Collection Test")
    assert booklist.id is not None
    booklist_id = booklist.id
    assert booklist.collection_count == 0
    await service.update_collection_count(booklist_id, +1)
    updated = await service.get_booklist(booklist_id)
    assert updated is not None
    assert updated.collection_count == 1
    await service.update_collection_count(booklist_id, -1)
    updated = await service.get_booklist(booklist_id)
    assert updated is not None
    assert updated.collection_count == 0
    # 不应低于0
    await service.update_collection_count(booklist_id, -5)
    updated = await service.get_booklist(booklist_id)
    assert updated is not None
    assert updated.collection_count == 0


# ============================================================
# 单帖多书单操作测试
# ============================================================


@pytest.mark.asyncio
async def test_add_thread_to_booklists(seeded_db_session: AsyncSession):
    """测试将一个帖子批量添加到多个书单"""
    service = BooklistRepository(seeded_db_session)
    booklist1 = await service.create_booklist(owner_id=100, title="BL1")
    assert booklist1.id is not None
    bid1 = booklist1.id
    booklist2 = await service.create_booklist(owner_id=100, title="BL2")
    assert booklist2.id is not None
    bid2 = booklist2.id
    booklist3 = await service.create_booklist(owner_id=100, title="BL3")
    assert booklist3.id is not None
    bid3 = booklist3.id
    # booklist2 先已包含 thread_id=1001
    await service.add_threads_to_booklist(
        bid2, items=[BooklistItemAddData(thread_id=1001)]
    )

    # 批量添加到三个书单
    added = await service.add_thread_to_booklists(
        thread_id=1001,
        booklist_ids=[bid1, bid2, bid3],
        owner_id=100,
        comment="批量推荐语",
    )
    assert sorted(added) == sorted([bid1, bid3])  # bid2 已存在，跳过

    # 检查 item_count
    bl1 = await service.get_booklist(bid1)
    bl2 = await service.get_booklist(bid2)
    bl3 = await service.get_booklist(bid3)
    assert bl1 is not None and bl2 is not None and bl3 is not None
    assert bl1.item_count == 1
    assert bl2.item_count == 1  # 未变（已存在的未重复插入）
    assert bl3.item_count == 1

    # 新增书单项在插入时直接写入推荐语
    statement = select(BooklistItem).where(
        BooklistItem.thread_id == 1001,
        BooklistItem.booklist_id.in_([bid1, bid3]),
    )
    items = (await seeded_db_session.execute(statement)).scalars().all()
    assert len(items) == 2
    assert all(item.comment == "批量推荐语" for item in items)


@pytest.mark.asyncio
async def test_add_thread_to_booklists_empty(seeded_db_session: AsyncSession):
    """测试空列表不会报错"""
    service = BooklistRepository(seeded_db_session)
    added = await service.add_thread_to_booklists(
        thread_id=1001, booklist_ids=[], owner_id=100
    )
    assert added == []


@pytest.mark.asyncio
async def test_remove_thread_from_booklists(seeded_db_session: AsyncSession):
    """测试将一个帖子从多个书单中批量移除"""
    service = BooklistRepository(seeded_db_session)
    booklist1 = await service.create_booklist(owner_id=200, title="BL1")
    assert booklist1.id is not None
    bid1 = booklist1.id
    booklist2 = await service.create_booklist(owner_id=200, title="BL2")
    assert booklist2.id is not None
    bid2 = booklist2.id
    booklist3 = await service.create_booklist(owner_id=200, title="BL3")
    assert booklist3.id is not None
    bid3 = booklist3.id
    # 三个书单都添加 thread_id=1001
    for bid in [bid1, bid2, bid3]:
        await service.add_threads_to_booklist(
            bid, items=[BooklistItemAddData(thread_id=1001)]
        )

    # 从 bid1 和 bid3 移除
    removed = await service.remove_thread_from_booklists(
        thread_id=1001, booklist_ids=[bid1, bid3]
    )
    assert sorted(removed) == sorted([bid1, bid3])

    # 检查 item_count
    bl1 = await service.get_booklist(bid1)
    bl2 = await service.get_booklist(bid2)
    bl3 = await service.get_booklist(bid3)
    assert bl1 is not None and bl2 is not None and bl3 is not None
    assert bl1.item_count == 0
    assert bl2.item_count == 1  # 未被移除
    assert bl3.item_count == 0


@pytest.mark.asyncio
async def test_remove_thread_from_booklists_empty(seeded_db_session: AsyncSession):
    """测试空列表不会报错"""
    service = BooklistRepository(seeded_db_session)
    removed = await service.remove_thread_from_booklists(
        thread_id=1001, booklist_ids=[]
    )
    assert removed == []


# ============================================================
# Service 层 sync_thread_in_booklists 测试
# ============================================================


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_mixed(seeded_db_session: AsyncSession):
    """完全同步：混合添加、移除、不变"""
    service = BooklistRepository(seeded_db_session)
    # 创建 4 个书单
    ids = []
    for i in range(4):
        bl = await service.create_booklist(owner_id=300, title=f"BL{i}")
        assert bl.id is not None
        ids.append(bl.id)

    # 书单 0 和 2 已有帖子 1001
    await service.add_threads_to_booklist(
        ids[0], items=[BooklistItemAddData(thread_id=1001)]
    )
    await service.add_threads_to_booklist(
        ids[2], items=[BooklistItemAddData(thread_id=1001)]
    )

    # 目标：修改后书单 0 和 1 包含帖子 1001
    scope = ids  # [0, 1, 2, 3]
    target = [ids[0], ids[1]]

    svc = BooklistService(seeded_db_session)
    result = await svc.sync_thread_in_booklists(
        user_id=300,
        thread_id=1001,
        scope_booklist_ids=scope,
        target_booklist_ids=target,
    )

    # 结果验证
    assert result.thread_id == 1001
    assert sorted(result.added_to_booklist_ids) == sorted([ids[1]])  # BL1 新增
    assert sorted(result.removed_from_booklist_ids) == sorted([ids[2]])  # BL2 移除
    assert sorted(result.unchanged_booklist_ids) == sorted(
        [ids[0], ids[3]]
    )  # BL0 已有/BL3 无且不在 target


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_pure_add(seeded_db_session: AsyncSession):
    """纯添加：target 中书单都不含该帖"""
    service = BooklistRepository(seeded_db_session)
    ids = []
    for i in range(3):
        bl = await service.create_booklist(owner_id=400, title=f"BL{i}")
        assert bl.id is not None
        ids.append(bl.id)

    # 无书单包含帖子 1001

    svc = BooklistService(seeded_db_session)
    result = await svc.sync_thread_in_booklists(
        user_id=400,
        thread_id=1001,
        scope_booklist_ids=ids,
        target_booklist_ids=[ids[0], ids[2]],
    )

    assert sorted(result.added_to_booklist_ids) == sorted([ids[0], ids[2]])
    assert result.removed_from_booklist_ids == []
    assert sorted(result.unchanged_booklist_ids) == sorted([ids[1]])


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_updates_comment(
    seeded_db_session: AsyncSession,
):
    """同步推荐语应同时覆盖新增项和已有项。"""
    repository = BooklistRepository(seeded_db_session)
    existing_booklist = await repository.create_booklist(owner_id=450, title="已有")
    assert existing_booklist.id is not None
    existing_booklist_id = existing_booklist.id
    new_booklist = await repository.create_booklist(owner_id=450, title="新增")
    assert new_booklist.id is not None
    new_booklist_id = new_booklist.id
    await repository.add_threads_to_booklist(
        existing_booklist_id,
        items=[BooklistItemAddData(thread_id=1001, comment="旧推荐语")],
    )

    service = BooklistService(seeded_db_session)
    await service.sync_thread_in_booklists(
        user_id=450,
        thread_id=1001,
        scope_booklist_ids=[existing_booklist_id, new_booklist_id],
        target_booklist_ids=[existing_booklist_id, new_booklist_id],
        comment="新推荐语",
    )

    for booklist_id in [existing_booklist_id, new_booklist_id]:
        statement = select(BooklistItem).where(
            BooklistItem.booklist_id == booklist_id,
            BooklistItem.thread_id == 1001,
        )
        item = (await seeded_db_session.execute(statement)).scalar_one()
        assert item.comment == "新推荐语"


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_pure_remove(seeded_db_session: AsyncSession):
    """纯删除：target 为空，移除 scope 中所有含该帖的书单"""
    service = BooklistRepository(seeded_db_session)
    ids = []
    for i in range(3):
        bl = await service.create_booklist(owner_id=500, title=f"BL{i}")
        assert bl.id is not None
        ids.append(bl.id)

    # 三个书单都包含帖子 1001
    for bid in ids:
        await service.add_threads_to_booklist(
            bid, items=[BooklistItemAddData(thread_id=1001)]
        )

    svc = BooklistService(seeded_db_session)
    result = await svc.sync_thread_in_booklists(
        user_id=500,
        thread_id=1001,
        scope_booklist_ids=ids,
        target_booklist_ids=[],
    )

    assert result.added_to_booklist_ids == []
    assert sorted(result.removed_from_booklist_ids) == sorted(ids)
    assert result.unchanged_booklist_ids == []


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_idempotent(seeded_db_session: AsyncSession):
    """幂等：同样参数调用两次，第二次无变更"""
    service = BooklistRepository(seeded_db_session)
    ids = []
    for i in range(2):
        bl = await service.create_booklist(owner_id=600, title=f"BL{i}")
        assert bl.id is not None
        ids.append(bl.id)

    # BL0 已有帖子，BL1 无
    await service.add_threads_to_booklist(
        ids[0], items=[BooklistItemAddData(thread_id=1001)]
    )

    scope = ids
    target = [ids[0], ids[1]]

    svc = BooklistService(seeded_db_session)
    # 第一次
    result1 = await svc.sync_thread_in_booklists(
        user_id=600,
        thread_id=1001,
        scope_booklist_ids=scope,
        target_booklist_ids=target,
    )
    assert sorted(result1.added_to_booklist_ids) == sorted([ids[1]])
    assert result1.removed_from_booklist_ids == []
    assert result1.unchanged_booklist_ids == [ids[0]]

    # 第二次：完全相同参数
    result2 = await svc.sync_thread_in_booklists(
        user_id=600,
        thread_id=1001,
        scope_booklist_ids=scope,
        target_booklist_ids=target,
    )
    assert result2.added_to_booklist_ids == []
    assert result2.removed_from_booklist_ids == []
    assert sorted(result2.unchanged_booklist_ids) == sorted([ids[0], ids[1]])


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_target_not_subset(
    seeded_db_session: AsyncSession,
):
    """target 不是 scope 的子集 → 422"""
    service = BooklistRepository(seeded_db_session)
    bl = await service.create_booklist(owner_id=700, title="BL")
    assert bl.id is not None

    svc = BooklistService(seeded_db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.sync_thread_in_booklists(
            user_id=700,
            thread_id=1001,
            scope_booklist_ids=[bl.id],
            target_booklist_ids=[bl.id, 99999],  # 99999 不在 scope 中
        )
    assert exc_info.value.status_code == 422
    assert "不在 scope 中" in exc_info.value.detail


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_not_owner(seeded_db_session: AsyncSession):
    """scope 中书单不属于当前用户 → 403"""
    service = BooklistRepository(seeded_db_session)
    bl = await service.create_booklist(owner_id=800, title="BL")
    assert bl.id is not None

    svc = BooklistService(seeded_db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.sync_thread_in_booklists(
            user_id=999,  # 不是 owner
            thread_id=1001,
            scope_booklist_ids=[bl.id],
            target_booklist_ids=[bl.id],
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_empty_scope(seeded_db_session: AsyncSession):
    """scope 为空 → 422"""
    svc = BooklistService(seeded_db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.sync_thread_in_booklists(
            user_id=900,
            thread_id=1001,
            scope_booklist_ids=[],
            target_booklist_ids=[],
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_sync_thread_in_booklists_nonexistent_in_scope(
    seeded_db_session: AsyncSession,
):
    """scope 中包含不存在的书单 → 404"""
    svc = BooklistService(seeded_db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.sync_thread_in_booklists(
            user_id=900,
            thread_id=1001,
            scope_booklist_ids=[99999],  # 不存在的书单
            target_booklist_ids=[99999],
        )
    assert exc_info.value.status_code == 404
