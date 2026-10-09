"""书单发布功能测试"""

import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import delete

from models import Author, Booklist, BooklistItem, BooklistPublish, Thread
from api.v1.routers import booklists as booklists_router
from core.booklist_publish_repository import BooklistPublishRepository
from core.booklist_repository import BooklistRepository
from booklist.booklist_publish_service import BooklistPublishService
from shared.enum.booklist_publish_status import BooklistPublishStatus
from shared.time_utils import utc_now


# ============================================================
# Fixtures
# ============================================================


@pytest_asyncio.fixture(scope="function")
async def seeded_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """提供包含基础测试数据的会话"""
    async with db_session_factory() as session:
        author = Author(
            id=1,
            name="TestAuthor",
            global_name="TestGlobal",
            display_name="TestDisplay",
            avatar_url="https://example.com/avatar.png",
        )
        session.add(author)
        threads = [
            Thread(
                channel_id=100,
                thread_id=1001,
                title="Thread 1",
                author_id=1,
                created_at=utc_now(),
                reaction_count=5,
                reply_count=2,
            ),
            Thread(
                channel_id=100,
                thread_id=1002,
                title="Thread 2",
                author_id=1,
                created_at=utc_now(),
                reaction_count=10,
                reply_count=3,
            ),
        ]
        session.add_all(threads)
        await session.commit()

        yield session

        # 清理
        await session.execute(delete(BooklistPublish))
        await session.execute(delete(BooklistItem))
        await session.execute(delete(Booklist))
        await session.execute(delete(Thread))
        await session.execute(delete(Author))
        await session.commit()


@pytest_asyncio.fixture(scope="function")
async def booklist(seeded_session: AsyncSession) -> Booklist:
    """创建一个测试书单"""
    repo = BooklistRepository(seeded_session)
    bl = await repo.create_booklist(
        owner_id=123,
        title="Test Booklist",
        description="Test desc",
        cover_image_url="https://example.com/cover.jpg",
    )
    assert bl.id is not None
    # 添加一个帖子
    from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData

    await repo.add_threads_to_booklist(
        bl.id, items=[BooklistItemAddData(thread_id=1001, comment="Nice thread")]
    )
    await seeded_session.refresh(bl)
    return bl


# ============================================================
# BooklistPublishRepository 测试
# ============================================================


@pytest.mark.asyncio
async def test_upsert_creates_new_record(seeded_session: AsyncSession):
    """测试 upsert 创建新记录"""
    repo = BooklistPublishRepository(seeded_session)
    record = await repo.upsert(
        booklist_id=1, guild_id=100, thread_id=200, discord_user_id=999
    )
    assert record.id is not None
    assert record.booklist_id == 1
    assert record.guild_id == 100
    assert record.thread_id == 200
    assert record.discord_user_id == 999


@pytest.mark.asyncio
async def test_upsert_idempotent(seeded_session: AsyncSession):
    """测试 upsert 幂等：相同 booklist_id + thread_id 更新记录"""
    repo = BooklistPublishRepository(seeded_session)
    # 首次创建
    r1 = await repo.upsert(
        booklist_id=1, guild_id=100, thread_id=200, discord_user_id=999
    )
    first_updated_at = r1.updated_at
    first_record_id = r1.id
    # 再次调用：同一目标更新 discord_user_id
    r2 = await repo.upsert(
        booklist_id=1, guild_id=100, thread_id=200, discord_user_id=777
    )
    assert r2.id == first_record_id  # 同一条记录
    assert r2.guild_id == 100
    assert r2.discord_user_id == 777  # 已更新
    assert r2.updated_at > first_updated_at


@pytest.mark.asyncio
async def test_upsert_different_threads(seeded_session: AsyncSession):
    """测试同一书单更换目标时删除旧记录并创建新记录"""
    repo = BooklistPublishRepository(seeded_session)
    r1 = await repo.upsert(
        booklist_id=1, guild_id=100, thread_id=201, discord_user_id=999
    )
    r1.message_id = 301
    r1.message_url = "https://discord.com/channels/100/201/301"
    old_record_id = r1.id
    await seeded_session.commit()

    r2 = await repo.upsert(
        booklist_id=1, guild_id=100, thread_id=202, discord_user_id=999
    )
    assert r2.id != old_record_id
    assert r2.thread_id == 202
    assert r2.message_id is None
    assert r2.message_url is None


@pytest.mark.asyncio
async def test_upsert_same_target_preserves_message(seeded_session: AsyncSession):
    """测试重复发布到同一目标时保留既有消息信息"""
    repo = BooklistPublishRepository(seeded_session)
    r1 = await repo.upsert(
        booklist_id=1, guild_id=100, thread_id=201, discord_user_id=999
    )
    r1.message_id = 301
    r1.message_url = "https://discord.com/channels/100/201/301"
    await seeded_session.commit()
    await seeded_session.refresh(r1)
    first_updated_at = r1.updated_at
    first_record_id = r1.id

    r2 = await repo.upsert(
        booklist_id=1, guild_id=100, thread_id=201, discord_user_id=777
    )
    assert r2.id == first_record_id
    assert r2.discord_user_id == 777
    assert r2.message_id == 301
    assert r2.message_url == "https://discord.com/channels/100/201/301"
    assert r2.updated_at > first_updated_at


@pytest.mark.asyncio
async def test_booklist_id_unique_constraint(seeded_session: AsyncSession):
    """测试数据库拒绝同一书单并存两条发布记录"""
    seeded_session.add_all(
        [
            BooklistPublish(
                booklist_id=1,
                guild_id=100,
                thread_id=201,
                discord_user_id=999,
            ),
            BooklistPublish(
                booklist_id=1,
                guild_id=100,
                thread_id=202,
                discord_user_id=999,
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        await seeded_session.commit()
    await seeded_session.rollback()


@pytest.mark.asyncio
async def test_get_by_booklist(seeded_session: AsyncSession):
    """测试获取书单的唯一发布记录"""
    repo = BooklistPublishRepository(seeded_session)
    await repo.upsert(booklist_id=1, guild_id=100, thread_id=201, discord_user_id=999)
    await repo.upsert(booklist_id=1, guild_id=100, thread_id=202, discord_user_id=999)
    await repo.upsert(booklist_id=2, guild_id=100, thread_id=203, discord_user_id=888)

    record = await repo.get_by_booklist(1)
    assert record is not None
    assert record.thread_id == 202


@pytest.mark.asyncio
async def test_get_by_booklist_empty(seeded_session: AsyncSession):
    """测试未发布的空书单"""
    repo = BooklistPublishRepository(seeded_session)
    record = await repo.get_by_booklist(99999)
    assert record is None


@pytest.mark.asyncio
async def test_delete_by_booklist(seeded_session: AsyncSession):
    """测试删除书单的所有发布记录"""
    repo = BooklistPublishRepository(seeded_session)
    await repo.upsert(booklist_id=1, guild_id=100, thread_id=201, discord_user_id=999)
    await repo.upsert(booklist_id=2, guild_id=100, thread_id=203, discord_user_id=888)

    deleted = await repo.delete_by_booklist(1)
    assert deleted == 1

    remaining = await repo.get_by_booklist(1)
    assert remaining is None

    # 书单 2 不受影响
    other = await repo.get_by_booklist(2)
    assert other is not None
    assert other.thread_id == 203


@pytest.mark.asyncio
async def test_is_published(seeded_session: AsyncSession):
    """测试 is_published 返回正确的布尔值"""
    repo = BooklistPublishRepository(seeded_session)
    assert await repo.is_published(1) is False

    await repo.upsert(booklist_id=1, guild_id=100, thread_id=200, discord_user_id=999)
    assert await repo.is_published(1) is True


# ============================================================
# 级联删除测试
# ============================================================


@pytest.mark.asyncio
async def test_delete_booklist_cascades_publish_records(seeded_session: AsyncSession):
    """测试删除书单时级联删除发布记录"""
    booklist_repo = BooklistRepository(seeded_session)
    publish_repo = BooklistPublishRepository(seeded_session)

    bl = await booklist_repo.create_booklist(owner_id=123, title="Cascade Test")
    assert bl.id is not None
    booklist_id = bl.id

    await publish_repo.upsert(
        booklist_id=booklist_id, guild_id=100, thread_id=200, discord_user_id=999
    )
    assert await publish_repo.is_published(booklist_id) is True

    await booklist_repo.delete_booklist(booklist_id)

    assert await publish_repo.is_published(booklist_id) is False


@pytest.mark.asyncio
async def test_delete_published_booklist_schedules_global_unpublish(
    seeded_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """测试删除已发布书单后创建不带帖子地址的外部任务。"""
    booklist_repo = BooklistRepository(seeded_session)
    publish_repo = BooklistPublishRepository(seeded_session)
    booklist = await booklist_repo.create_booklist(owner_id=123, title="Published")
    assert booklist.id is not None
    booklist_id = booklist.id
    await publish_repo.upsert(booklist_id, 100, 200, 999)

    @asynccontextmanager
    async def session_factory():
        yield seeded_session

    schedule_unpublish = MagicMock()
    monkeypatch.setattr(booklists_router, "AsyncSessionFactory", session_factory)
    monkeypatch.setattr(
        BooklistPublishService, "schedule_unpublish", schedule_unpublish
    )

    result = await booklists_router.delete_booklist(
        booklist_id, current_user={"id": "123"}
    )

    assert result == {"message": "书单删除成功"}
    schedule_unpublish.assert_called_once_with(booklist_id)


@pytest.mark.asyncio
async def test_delete_unpublished_booklist_skips_external_call(
    seeded_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """测试删除未发布书单时不创建外部任务。"""
    booklist_repo = BooklistRepository(seeded_session)
    booklist = await booklist_repo.create_booklist(owner_id=123, title="Unpublished")
    assert booklist.id is not None
    booklist_id = booklist.id

    @asynccontextmanager
    async def session_factory():
        yield seeded_session

    schedule_unpublish = MagicMock()
    monkeypatch.setattr(booklists_router, "AsyncSessionFactory", session_factory)
    monkeypatch.setattr(
        BooklistPublishService, "schedule_unpublish", schedule_unpublish
    )

    result = await booklists_router.delete_booklist(
        booklist_id, current_user={"id": "123"}
    )

    assert result == {"message": "书单删除成功"}
    schedule_unpublish.assert_not_called()


@pytest.mark.asyncio
async def test_delete_booklist_failure_skips_external_call(
    seeded_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """测试本地删除失败时不创建外部任务。"""
    booklist_repo = BooklistRepository(seeded_session)
    publish_repo = BooklistPublishRepository(seeded_session)
    booklist = await booklist_repo.create_booklist(owner_id=123, title="Failure")
    assert booklist.id is not None
    booklist_id = booklist.id
    await publish_repo.upsert(booklist_id, 100, 200, 999)

    @asynccontextmanager
    async def session_factory():
        yield seeded_session

    schedule_unpublish = MagicMock()
    monkeypatch.setattr(booklists_router, "AsyncSessionFactory", session_factory)
    monkeypatch.setattr(
        BooklistRepository,
        "delete_booklist",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        BooklistPublishService, "schedule_unpublish", schedule_unpublish
    )

    with pytest.raises(booklists_router.HTTPException) as exc_info:
        await booklists_router.delete_booklist(booklist_id, current_user={"id": "123"})

    assert exc_info.value.status_code == 404
    schedule_unpublish.assert_not_called()


# ============================================================
# BooklistPublishService 测试
# ============================================================


@pytest.mark.asyncio
async def test_publish_sets_pending_status(
    seeded_session: AsyncSession, booklist: Booklist
):
    """测试 publish 将书单状态设为 PENDING"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(
        seeded_session,
        base_url="http://127.0.0.1:10820",
        api_key="test-key",
    )
    await svc.publish(booklist_id, guild_id=100, thread_id=200, discord_user_id=999)

    # 验证 publish_status 已更新
    repo = BooklistPublishRepository(seeded_session)
    assert await repo.is_published(booklist_id) is True

    # 刷新书单检查状态
    await seeded_session.refresh(booklist)
    assert booklist.publish_status == BooklistPublishStatus.PENDING.value


@pytest.mark.asyncio
async def test_publish_raises_when_not_configured(
    seeded_session: AsyncSession,
    booklist: Booklist,
):
    """测试 base_url 为空时 publish 抛出异常"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(seeded_session, base_url="", api_key="")
    with pytest.raises(ValueError, match="未配置"):
        await svc.publish(booklist_id, guild_id=100, thread_id=200, discord_user_id=999)


@pytest.mark.asyncio
async def test_publish_success_updates_current_record(
    seeded_session: AsyncSession, booklist: Booklist
):
    """测试当前发布请求成功后更新消息信息和状态"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(seeded_session, base_url="http://publisher")
    record = await svc.publish_repo.upsert(booklist_id, 100, 200, 999)
    assert record.id is not None
    record_id = record.id
    request_updated_at = record.updated_at
    await svc.booklist_repo.set_publish_status(
        booklist_id, BooklistPublishStatus.PENDING.value
    )

    await svc._on_api_success(
        seeded_session,
        booklist_id,
        200,
        record_id,
        request_updated_at,
        {
            "message_id": "300",
            "message_url": "https://discord.com/channels/100/200/300",
        },
    )

    current = await svc.publish_repo.get_by_booklist(booklist_id)
    assert current is not None
    assert current.message_id == 300
    await seeded_session.refresh(booklist)
    assert booklist.publish_status == BooklistPublishStatus.SUCCESS.value


@pytest.mark.asyncio
async def test_publish_failure_updates_current_status(
    seeded_session: AsyncSession, booklist: Booklist
):
    """测试当前发布请求失败后设置 FAILED"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(seeded_session, base_url="http://publisher")
    record = await svc.publish_repo.upsert(booklist_id, 100, 200, 999)
    assert record.id is not None
    record_id = record.id
    request_updated_at = record.updated_at
    await svc.booklist_repo.set_publish_status(
        booklist_id, BooklistPublishStatus.PENDING.value
    )

    await svc._on_api_failure(
        seeded_session, booklist_id, 200, record_id, request_updated_at
    )

    await seeded_session.refresh(booklist)
    assert booklist.publish_status == BooklistPublishStatus.FAILED.value


@pytest.mark.asyncio
async def test_stale_publish_callback_cannot_overwrite_latest_request(
    seeded_session: AsyncSession, booklist: Booklist
):
    """测试旧任务即使目标再次相同也不能覆盖最新发布请求"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(seeded_session, base_url="http://publisher")
    first = await svc.publish_repo.upsert(booklist_id, 100, 200, 999)
    assert first.id is not None
    first_record_id = first.id
    first_updated_at = first.updated_at
    await svc.publish_repo.upsert(booklist_id, 100, 201, 999)
    latest = await svc.publish_repo.upsert(booklist_id, 100, 200, 999)
    latest_record_id = latest.id
    latest_updated_at = latest.updated_at
    await svc.booklist_repo.set_publish_status(
        booklist_id, BooklistPublishStatus.PENDING.value
    )

    await svc._on_api_success(
        seeded_session,
        booklist_id,
        200,
        first_record_id,
        first_updated_at,
        {"message_id": "300", "message_url": "https://old-message"},
    )

    current = await svc.publish_repo.get_by_booklist(booklist_id)
    assert current is not None
    assert current.id == latest_record_id
    assert current.id != first_record_id
    assert current.updated_at == latest_updated_at
    assert current.message_id is None
    await seeded_session.refresh(booklist)
    assert booklist.publish_status == BooklistPublishStatus.PENDING.value


@pytest.mark.asyncio
async def test_same_target_stale_callback_cannot_overwrite_latest_request(
    seeded_session: AsyncSession, booklist: Booklist
):
    """测试同目标旧回调由 updated_at 识别并忽略"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(seeded_session, base_url="http://publisher")
    first = await svc.publish_repo.upsert(booklist_id, 100, 200, 999)
    assert first.id is not None
    first_record_id = first.id
    first_updated_at = first.updated_at
    latest = await svc.publish_repo.upsert(booklist_id, 100, 200, 999)
    latest_record_id = latest.id
    latest_updated_at = latest.updated_at
    await svc.booklist_repo.set_publish_status(
        booklist_id, BooklistPublishStatus.PENDING.value
    )

    await svc._on_api_failure(
        seeded_session,
        booklist_id,
        200,
        first_record_id,
        first_updated_at,
    )

    current = await svc.publish_repo.get_by_booklist(booklist_id)
    assert current is not None
    assert current.id == latest_record_id == first_record_id
    assert current.updated_at == latest_updated_at
    await seeded_session.refresh(booklist)
    assert booklist.publish_status == BooklistPublishStatus.PENDING.value


@pytest.mark.asyncio
async def test_unpublish_sets_none_status_and_schedules_external_call(
    seeded_session: AsyncSession,
    booklist: Booklist,
    monkeypatch: pytest.MonkeyPatch,
):
    """测试 unpublish 完成本地处理后按发布目标创建外部任务。"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(
        seeded_session,
        base_url="http://127.0.0.1:10820",
        api_key="test-key",
    )
    await svc.publish_repo.upsert(
        booklist_id, guild_id=100, thread_id=200, discord_user_id=999
    )
    await svc.booklist_repo.set_publish_status(
        booklist_id, BooklistPublishStatus.SUCCESS.value
    )
    schedule_unpublish = MagicMock()
    monkeypatch.setattr(svc, "schedule_unpublish", schedule_unpublish)

    await svc.unpublish(booklist_id)

    await seeded_session.refresh(booklist)
    assert booklist.publish_status == BooklistPublishStatus.NONE.value

    repo = BooklistPublishRepository(seeded_session)
    assert await repo.is_published(booklist_id) is False
    schedule_unpublish.assert_called_once_with(
        booklist_id,
        "https://discord.com/channels/100/200",
    )


@pytest.mark.asyncio
async def test_unpublish_without_record_does_not_schedule_external_call(
    seeded_session: AsyncSession,
    booklist: Booklist,
    monkeypatch: pytest.MonkeyPatch,
):
    """测试未发布书单仅完成本地处理，不创建外部任务。"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(seeded_session, base_url="http://publisher")
    schedule_unpublish = MagicMock()
    monkeypatch.setattr(svc, "schedule_unpublish", schedule_unpublish)

    await svc.unpublish(booklist_id)

    schedule_unpublish.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("thread_url", "expected_payload"),
    [
        (
            "https://discord.com/channels/100/200",
            {
                "booklist_id": 1,
                "thread_url": "https://discord.com/channels/100/200",
            },
        ),
        (None, {"booklist_id": 1}),
    ],
)
async def test_external_unpublish_request_payload(
    seeded_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    thread_url: str | None,
    expected_payload: dict,
):
    """测试外部取消发布请求的地址、鉴权和可选帖子地址。"""
    captured_request: httpx.Request | None = None

    def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={"ok": True, "requested": 1, "deleted": 1})

    transport = httpx.MockTransport(handle_request)
    async_client_type = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda: async_client_type(transport=transport),
    )
    svc = BooklistPublishService(
        seeded_session, base_url="http://publisher", api_key="test-key"
    )

    await svc._do_call_unpublish_api(1, thread_url)

    assert captured_request is not None
    assert captured_request.url == "http://publisher/booklist/unpublish"
    assert captured_request.headers["X-API-Key"] == "test-key"
    assert json.loads(captured_request.content) == expected_payload


@pytest.mark.asyncio
async def test_external_unpublish_failure_is_swallowed(
    seeded_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """测试外部取消发布失败不会向主流程抛出异常。"""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, json={"error": "bot not ready"})
    )
    async_client_type = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda: async_client_type(transport=transport),
    )
    svc = BooklistPublishService(seeded_session, base_url="http://publisher")

    await svc._do_call_unpublish_api(1)

    assert "调用取消发布 API 失败" in caplog.text


@pytest.mark.asyncio
async def test_sync_published_booklist_skips_when_not_published(
    seeded_session: AsyncSession,
    booklist: Booklist,
):
    """测试未发布书单的 sync 直接跳过"""
    assert booklist.id is not None
    booklist_id = booklist.id
    svc = BooklistPublishService(
        seeded_session,
        base_url="http://127.0.0.1:10820",
        api_key="test-key",
    )
    # 不应抛出异常
    await svc.sync_published_booklist(booklist_id)

    # 状态应保持为 NONE
    await seeded_session.refresh(booklist)
    assert booklist.publish_status == BooklistPublishStatus.NONE.value


@pytest.mark.asyncio
async def test_sync_published_booklist_skips_when_not_configured(
    seeded_session: AsyncSession,
):
    """测试 base_url 未配置时 sync 静默跳过"""
    svc = BooklistPublishService(seeded_session, base_url="", api_key="")
    # 不应抛出异常
    await svc.sync_published_booklist(99999)


@pytest.mark.asyncio
async def test_sync_triggers_on_add_thread(seeded_session: AsyncSession):
    """测试添加帖子后触发 _delayed_publish_sync"""
    repo = BooklistRepository(seeded_session)
    bl = await repo.create_booklist(owner_id=123, title="Sync Test")
    assert bl.id is not None
    booklist_id = bl.id

    # 先发布书单
    publish_repo = BooklistPublishRepository(seeded_session)
    await publish_repo.upsert(
        booklist_id=booklist_id, guild_id=100, thread_id=200, discord_user_id=999
    )

    # 添加帖子 - 应触发后台同步任务
    import asyncio
    from api.v1.schemas.booklist.booklist_item_add_data import BooklistItemAddData

    # 不等待后台任务完成，只验证不会崩溃
    await repo.add_threads_to_booklist(
        booklist_id, items=[BooklistItemAddData(thread_id=1002, comment="Test")]
    )
    # 给 asyncio.create_task 一个执行窗口
    await asyncio.sleep(0.1)


# ============================================================
# _parse_thread_url 测试
# ============================================================


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://discord.com/channels/123/456", (123, 456)),
        ("http://discord.com/channels/999/888", (999, 888)),
        ("https://www.discord.com/channels/1/2", (1, 2)),
    ],
)
def test_parse_thread_url_valid(url, expected):
    """测试解析有效 Discord 帖 URL"""
    from shared.thread_link_parser import ThreadLinkParser

    assert ThreadLinkParser.parse_thread_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "https://discord.com/channels/abc/def",
        "https://discord.com/channels/123",
        "https://other.com/channels/123/456",
    ],
)
def test_parse_thread_url_invalid(url):
    """测试解析无效 URL 抛出异常"""
    from shared.thread_link_parser import ThreadLinkParser

    with pytest.raises(ValueError, match="无效的 Discord 讨论帖 URL"):
        ThreadLinkParser.parse_thread_url(url)


# ============================================================
# BooklistSummary / BooklistDetail DTO 测试
# ============================================================


def test_booklist_detail_inherits_summary():
    """测试 BooklistDetail 继承 BooklistSummary"""
    from api.v1.schemas.booklist.booklist_summary import BooklistSummary
    from api.v1.schemas.booklist.booklist_detail import (
        BooklistDetail,
        BooklistPublishInfo,
    )

    assert issubclass(BooklistDetail, BooklistSummary)

    now = utc_now()
    detail = BooklistDetail(  # type: ignore[call-arg]
        id=1,
        owner_id=100,
        title="Test",
        is_public=True,
        is_anonymous=False,
        is_default=False,
        item_count=0,
        collection_count=0,
        view_count=0,
        created_at=now,
        updated_at=now,
    )
    assert detail.publish_info is None

    # 设置 publish_info
    detail.publish_info = BooklistPublishInfo(
        guild_id=100,
        thread_id=200,
        thread_url="https://discord.com/channels/100/200",
        message_id=None,
        message_url=None,
        published_at=utc_now(),
    )
    assert detail.publish_info.guild_id == 100


def test_booklist_summary_has_publish_status():
    """测试 BooklistSummary 包含 publish_status 字段"""
    from api.v1.schemas.booklist.booklist_summary import BooklistSummary

    now = utc_now()
    summary = BooklistSummary(  # type: ignore[call-arg]
        id=1,
        owner_id=100,
        title="Test",
        is_public=True,
        is_anonymous=False,
        is_default=False,
        item_count=0,
        collection_count=0,
        view_count=0,
        created_at=now,
        updated_at=now,
    )
    assert summary.publish_status == 0
    assert hasattr(summary, "publish_info") is False  # 列表 DTO 不应有 publish_info
