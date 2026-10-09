from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4
import asyncio
import importlib.util
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from conftest import TEST_DATABASE_URL
from core.tag_query import tag_filters
from core.tag_access_service import TagAccessService
from core.tag_repository import TagRepository
from dto.events.tag_command import TagCommand
from models import Booklist, Notification, Thread
from core.thread_repository import ThreadRepository
from models.tag_binding import TagBinding
from models.operation_log import OperationLog
from models.tag_proposal import TagProposal
from shared.tag_error import TagError
from shared.tag_rules import validate_graph, validate_selection
from shared.time_utils import utc_now
from tag.tag_runtime import create_tag_mediator
from tag.tag_worker import TagWorker


@pytest_asyncio.fixture
async def setup_tags(monkeypatch):
    """在独立临时 schema 验证真实 PostgreSQL 事务，不接触现有表。"""
    schema = "test_custom_tags_" + uuid4().hex
    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"server_settings": {"search_path": schema}}
    )
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    config = {
        "main_guild_id": 10,
        "bot_admin_user_ids": [99],
        "management_role_id": "manager",
        "auth": {"role_ids": ["member"]},
    }

    async def roles(self, user_id, guild_id):
        return {"member", "manager"} if user_id == 2 else {"member"}

    monkeypatch.setattr(TagAccessService, "roles", roles)
    async with factory() as session, session.begin():
        session.add(
            Thread(
                id=100,
                thread_id=100,
                guild_id=10,
                channel_id=20,
                author_id=1,
                title="测试",
                show_flag=True,
            )
        )
        session.add(Booklist(id=1, owner_id=1, title="书单", is_public=True))
    mediator = create_tag_mediator(factory, config)

    async def call(action, actor=1, **payload):
        return await mediator.request(TagCommand(action, actor, payload))

    try:
        yield factory, config, call
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await engine.dispose()


async def create(call, name="爱丽丝(BA)", **kwargs):
    """创建供各场景使用的标准标签。"""
    return await call("manage", 99, operation="create", name=name, category=3, **kwargs)


async def attach(call, tag_ids, kind="thread", tid=100, actor=1):
    """按读到的版本提交目标集合。"""
    current = await call("read", actor, target_type=kind, target_id=tid)
    return await call(
        "replace",
        actor,
        target_type=kind,
        target_id=tid,
        version=current["version"],
        tag_ids=tag_ids,
    )


def test_selection_and_graph_rules():
    """验证上限、互斥与循环，允许纯删除历史超限集合。"""
    tags = {i: SimpleNamespace(enabled=True, deleted_at=None) for i in range(1, 20)}
    validate_selection(set(range(1, 14)), set(range(1, 13)), 2, tags, [])
    with pytest.raises(TagError, match="12"):
        validate_selection(set(), set(range(1, 13)), 1, tags, [])
    with pytest.raises(TagError, match="互斥"):
        validate_selection({1}, {1, 2}, 0, tags, [(1, 2)])
    validate_graph([(1, 2), (1, 3), (2, 4), (3, 4)])
    with pytest.raises(TagError, match="循环"):
        validate_graph([(1, 2), (2, 3), (3, 1)])


@pytest.mark.asyncio
async def test_internal_id_and_alias_lifecycle(setup_tags):
    """验证原生 ID 映射、别名多候选和软删除恢复不复活绑定。"""
    factory, _, call = setup_tags
    async with factory() as session, session.begin():
        native = (
            await TagRepository(session).get_or_create_tags(
                {123456789012345678: "原生"}, channel_id=20
            )
        )[0]
        internal = native.id
        assert internal > 0 and internal != 9007199254740993
        again = (
            await TagRepository(session).get_or_create_tags(
                {123456789012345678: "改名"}, channel_id=20
            )
        )[0]
        assert again.id == internal
    a = await create(call, aliases=["Alice", "アリス"])
    await create(call, "爱丽丝(SAO)", aliases=["Alice"])
    assert len(await call("pool", q="Alice")) == 2
    await attach(call, [a["id"]])
    await call("manage", 99, operation="delete", tag_id=a["id"])
    with pytest.raises(TagError) as error:
        await create(call)
    assert error.value.detail["code"] == "deleted_tag_exists"
    assert error.value.detail["tag_id"] == a["id"]
    await call("manage", 99, operation="restore", tag_id=a["id"])
    assert not (await call("read", target_type="thread", target_id=100))["tags"]
    async with factory() as session:
        history = (await session.execute(select(TagBinding))).scalar_one()
        assert history.end_reason == "tag_deleted"


@pytest.mark.asyncio
async def test_abyss_pool_relations_and_bound_snapshot(setup_tags):
    """候选和关系按身份隐藏，既有绑定与方向切换不受影响。"""
    _, _, call = setup_tags
    normal = await create(call, name="正常")
    abyss = await create(call, name="深渊", is_abyss=True)
    await call(
        "manage",
        99,
        operation="add_relation",
        tag_id=normal["id"],
        target_tag_id=abyss["id"],
        kind="implies",
    )

    assert {item["name"] for item in await call("pool")} == {"正常"}
    assert await call("relations") == []
    visible = await call("pool", _can_view_abyss=True)
    assert {item["name"] for item in visible} == {"正常", "深渊"}
    assert len(await call("relations", _can_view_abyss=True)) == 1

    result = await attach(call, [abyss["id"]])
    assert result["tags"][0]["is_abyss"] is True
    binding_id = result["tags"][0]["binding_id"]
    updated = await call(
        "manage",
        99,
        operation="update",
        tag_id=abyss["id"],
        is_abyss=False,
    )
    assert updated["is_abyss"] is False
    after = await call("read", target_type="thread", target_id=100)
    assert after["tags"][0]["binding_id"] == binding_id
    assert after["tags"][0]["is_abyss"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,tid", [("thread", 100), ("booklist", 1)])
async def test_votes_rounds_and_proposal_block(setup_tags, kind, tid):
    """验证所有来源标签净负六票下标、重挂清票及永久重提限制。"""
    _, _, call = setup_tags
    tag = await create(call)
    result = await attach(call, [tag["id"]], kind, tid)
    binding = result["tags"][0]["binding_id"]
    for actor in range(10, 15):
        await call(
            "vote", actor, target_type=kind, target_id=tid, binding_id=binding, vote=-1
        )
    assert (await call("read", target_type=kind, target_id=tid))["tags"][0][
        "downvotes"
    ] == 5
    await call("vote", 1, target_type=kind, target_id=tid, binding_id=binding, vote=1)
    await call("vote", 1, target_type=kind, target_id=tid, binding_id=binding, vote=1)
    assert (await call("read", target_type=kind, target_id=tid))["tags"][0][
        "upvotes"
    ] == 1
    await call("vote", 1, target_type=kind, target_id=tid, binding_id=binding, vote=0)
    await call("vote", 15, target_type=kind, target_id=tid, binding_id=binding, vote=-1)
    assert not (await call("read", target_type=kind, target_id=tid))["tags"]
    with pytest.raises(TagError) as error:
        await call("propose", 3, target_type=kind, target_id=tid, tag_id=tag["id"])
    assert error.value.detail["code"] == "proposal_blocked"
    result = await attach(call, [tag["id"]], kind, tid, actor=2)
    assert result["tags"][0]["downvotes"] == 0
    assert result["tags"][0]["binding_id"] != binding
    with pytest.raises(TagError):
        await call(
            "vote", 10, target_type=kind, target_id=tid, binding_id=binding, vote=0
        )


@pytest.mark.asyncio
async def test_proposals_timeout_and_notifications(setup_tags):
    """验证非公开审核、拒绝重提、七天生效及站内通知兜底。"""
    factory, config, call = setup_tags
    tag = await create(call)
    payload = {"target_type": "booklist", "target_id": 1}
    proposal = await call("propose", 3, **payload, tag_id=tag["id"])
    assert not (await call("read", **payload))["tags"]
    assert await call("proposals", 4, **payload) == []
    with pytest.raises(TagError):
        await call("proposals", 3, **payload, review_queue=True)
    await call("review", **payload, proposal_id=proposal["id"], approve=False)
    proposal = await call("propose", 3, **payload, tag_id=tag["id"])
    worker = TagWorker(factory, config)

    async def failed_send(proposal):
        return False

    await worker.deliver(failed_send)
    await worker.deliver(failed_send)
    async with factory() as session, session.begin():
        notice = (await session.execute(select(Notification))).scalar_one()
        assert notice.target_type == "booklist" and notice.user_id == 1
        row = await session.get(TagProposal, int(proposal["id"]))
        row.due_at = utc_now() + timedelta(seconds=10)
    await worker.expire()
    assert not (await call("read", **payload))["tags"]
    async with factory() as session, session.begin():
        row = await session.get(TagProposal, int(proposal["id"]))
        row.due_at = utc_now() - timedelta(seconds=1)
    await worker.expire()
    assert (await call("read", **payload))["tags"][0]["id"] == tag["id"]
    await worker.expire()
    async with factory() as session:
        assert len((await session.execute(select(TagBinding))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_versions_permissions_and_search(setup_tags):
    """验证过期写入、作者审计限制及筛选状态。"""
    factory, _, call = setup_tags
    tag = await create(call)
    before = await call("read", target_type="thread", target_id=100)
    await attach(call, [tag["id"]])
    with pytest.raises(TagError) as error:
        await call(
            "replace",
            target_type="thread",
            target_id=100,
            version=before["version"],
            tag_ids=[],
        )
    assert error.value.detail["code"] == "stale_version"
    with pytest.raises(TagError):
        await call("audit", target_type="thread", target_id=100)
    assert await call("audit", 2, target_type="thread", target_id=100)
    with pytest.raises(TagError):
        await attach(call, [], actor=3)
    await call("manage", 99, operation="disable", tag_id=tag["id"])
    async with factory() as session:
        query = select(Thread).where(*tag_filters("thread", Thread.id, [tag["id"]], []))
        assert (await session.execute(query)).scalar_one().thread_id == 100
    await call("manage", 99, operation="delete", tag_id=tag["id"])
    async with factory() as session:
        assert (await session.execute(query)).scalar_one_or_none() is None
        assert (await session.execute(select(OperationLog))).first() is not None


@pytest.mark.asyncio
async def test_concurrent_votes_and_stale_empty_version(setup_tags):
    """并发下标只结束一次，空集合来回变化也使旧版本失效。"""
    factory, _, call = setup_tags
    tag = await create(call)
    payload = {"target_type": "thread", "target_id": 100}
    initial = await call("read", **payload)
    binding = (await attach(call, [tag["id"]]))["tags"][0]["binding_id"]
    await asyncio.gather(
        *[
            call("vote", actor, **payload, binding_id=binding, vote=-1)
            for actor in range(10, 16)
        ]
    )
    assert not (await call("read", **payload))["tags"]
    with pytest.raises(TagError) as error:
        await call(
            "replace", **payload, version=initial["version"], tag_ids=[tag["id"]]
        )
    assert error.value.detail["code"] == "stale_version"
    async with factory() as session:
        ends = list(
            (
                await session.execute(
                    select(OperationLog).where(OperationLog.type == "tag.unbind")
                )
            ).scalars()
        )
        assert len(ends) == 1 and ends[0].detail["downvotes"] == 6


@pytest.mark.asyncio
async def test_native_sync_overflow_and_relationships(setup_tags):
    """原生同步保留自定义绑定，超限只许删，包含关系不自动挂标。"""
    factory, _, call = setup_tags
    tags = [await create(call, f"角色{i}") for i in range(13)]
    ids = [t["id"] for t in tags]
    await call(
        "manage",
        99,
        operation="add_relation",
        tag_id=ids[0],
        target_tag_id=ids[1],
        kind="implies",
    )
    result = await attach(call, [ids[0]])
    assert len(result["tags"]) == 1
    with pytest.raises(TagError):
        await call(
            "manage",
            99,
            operation="add_relation",
            tag_id=ids[1],
            target_tag_id=ids[0],
            kind="implies",
        )
    await attach(call, ids[:11])
    async with factory() as session, session.begin():
        native = await TagRepository(session).get_or_create_tags(
            {9001: "原生1", 9002: "原生2"}, channel_id=20
        )
        await ThreadRepository(session).add_or_update_thread_with_tags(
            {"thread_id": 100}, native
        )
    result = await call("read", target_type="thread", target_id=100)
    assert len(result["tags"]) == 13
    with pytest.raises(TagError):
        await attach(call, ids[:12])
    assert len((await attach(call, ids[:10]))["tags"]) == 12
    await call(
        "manage",
        99,
        operation="add_relation",
        tag_id=ids[0],
        target_tag_id=ids[12],
        kind="excludes",
    )
    with pytest.raises(TagError):
        await attach(call, [ids[0], ids[12]])


@pytest.mark.asyncio
async def test_timeout_disabled_tag_ends_without_binding(setup_tags):
    """审核期间停用的标签到期后失败，不会重新挂回。"""
    factory, config, call = setup_tags
    tag = await create(call)
    proposal = await call(
        "propose", 3, target_type="thread", target_id=100, tag_id=tag["id"]
    )
    await call("manage", 99, operation="disable", tag_id=tag["id"])
    async with factory() as session, session.begin():
        row = await session.get(TagProposal, int(proposal["id"]))
        row.due_at = utc_now() - timedelta(seconds=1)
    await TagWorker(factory, config).expire()
    statuses = await call("proposals", 3, target_type="thread", target_id=100)
    assert statuses[0]["status"] == "failed"
    assert statuses[0]["reason"] == "unavailable_tags"


@pytest.mark.asyncio
async def test_management_visibility_and_private_booklist(setup_tags):
    """管理组可管理隐藏内容，普通用户不能读取私有书单标签。"""
    factory, _, call = setup_tags
    tag = await create(call)
    async with factory() as session, session.begin():
        thread = (await session.execute(select(Thread))).scalar_one()
        thread.show_flag = False
        booklist = await session.get(Booklist, 1)
        booklist.is_public = False
    with pytest.raises(TagError):
        await call("read", 3, target_type="thread", target_id=100)
    with pytest.raises(TagError):
        await call("read", 3, target_type="booklist", target_id=1)
    assert (await attach(call, [tag["id"]], actor=2))["tags"]
    assert (await attach(call, [tag["id"]], kind="booklist", tid=1, actor=1))["tags"]


@pytest.mark.asyncio
async def test_unified_tag_filter_mixed_sources(setup_tags):
    """混合来源标签统一计算 AND、OR、排除，不混淆帖子内部与 Discord ID。"""
    from core.booklist_repository import BooklistRepository
    from api.v1.schemas.search.search_request import SearchRequest

    factory, _, call = setup_tags
    async with factory() as session, session.begin():
        native = await TagRepository(session).get_or_create_tags(
            {987654321012345678: "原生筛选"}, channel_id=20
        )
        native_id = native[0].id
        for tid in (100, 200, 300):
            await ThreadRepository(session).add_or_update_thread_with_tags(
                {
                    "thread_id": tid,
                    "guild_id": 10,
                    "channel_id": 20,
                    "author_id": 1,
                    "title": str(tid),
                    "show_flag": True,
                },
                native if tid != 300 else [],
            )
    custom = await create(call)
    custom_id = int(custom["id"])
    for tid in (100, 300):
        await attach(call, [custom_id], tid=tid)
    await attach(call, [custom_id], kind="booklist", tid=1)

    async def matched(included, excluded=(), logic="and"):
        async with factory() as session:
            query = select(Thread.thread_id).where(
                *tag_filters("thread", Thread.id, included, excluded, logic)
            )
            return set((await session.execute(query)).scalars())

    assert await matched([native_id, custom_id]) == {100}
    assert await matched([native_id, custom_id], logic="or") == {100, 200, 300}
    assert await matched([native_id, custom_id], [native_id], "or") == {300}
    assert await matched([], [custom_id]) == {200}
    assert await matched([native_id]) == {100, 200}
    assert await matched([custom_id, 999999]) == set()
    async with factory() as session:
        repo = BooklistRepository(session)
        _, count = await repo.list_booklists(
            include_tag_ids=[native_id, custom_id], tag_logic="or"
        )
        assert count == 1
        _, count = await repo.list_booklists(
            include_tag_ids=[native_id, custom_id], tag_logic="and"
        )
        assert count == 0
    request = SearchRequest(include_tag_ids=[str(native_id), str(custom_id)])
    assert request.include_tag_ids == [native_id, custom_id]
    properties = SearchRequest.model_json_schema()["properties"]
    assert (
        "include_custom_tag_ids" not in properties
        and "exclude_custom_tag_ids" not in properties
    )


@pytest.mark.asyncio
async def test_legacy_migration_preserves_keys(setup_tags):
    """实际执行迁移并验证旧关联主键与新序列分配。"""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    factory, _, _ = setup_tags
    schema = "test_tag_migration_" + uuid4().hex
    path = Path(__file__).parents[1] / "alembic/versions/add_custom_tag_governance.py"
    spec = importlib.util.spec_from_file_location("tag_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    old_id = 123456789012345678
    async with factory() as session, session.begin():
        await session.execute(text(f'CREATE SCHEMA "{schema}"'))
        await session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        await session.execute(
            text("CREATE TABLE tag (id BIGINT PRIMARY KEY, name VARCHAR NOT NULL)")
        )
        await session.execute(
            text(
                "CREATE TABLE thread (id INTEGER PRIMARY KEY, channel_id BIGINT NOT NULL)"
            )
        )
        await session.execute(
            text("CREATE TABLE thread_tag_link (thread_id INTEGER, tag_id BIGINT)")
        )
        await session.execute(
            text(
                "CREATE TABLE notification (id SERIAL PRIMARY KEY, thread_id BIGINT NOT NULL, event_type VARCHAR, CONSTRAINT ck_notification_event_type CHECK (event_type IN ('thread_update', 'author_new_thread')))"
            )
        )
        await session.execute(
            text("INSERT INTO tag VALUES (:id, '旧标签')"), {"id": old_id}
        )
        await session.execute(text("INSERT INTO thread VALUES (1, 20)"))
        await session.execute(
            text("CREATE TABLE tag_vote (id SERIAL PRIMARY KEY, vote INTEGER)")
        )
        await session.execute(text("INSERT INTO tag_vote (vote) VALUES (1)"))
        await session.execute(
            text("INSERT INTO thread_tag_link VALUES (1, :id)"), {"id": old_id}
        )
        connection = await session.connection()

        def upgrade(conn):
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()

        await connection.run_sync(upgrade)
        row = (await session.execute(text("SELECT id, discord_tag_id FROM tag"))).one()
        assert row == (old_id, old_id)
        new_id = (
            await session.execute(
                text(
                    "INSERT INTO tag (name,source,category) VALUES ('新标签','custom',1) RETURNING id"
                )
            )
        ).scalar_one()
        assert new_id == old_id + 1
        assert (
            await session.execute(text("SELECT tag_id FROM thread_tag_link"))
        ).scalar_one() == old_id
        binding = (
            await session.execute(
                text(
                    "SELECT target_id, tag_id, binding_source, upvotes, downvotes FROM tag_binding"
                )
            )
        ).one()
        assert binding == (1, old_id, "discord_sync", 0, 0)
        assert (
            await session.execute(text("SELECT count(*) FROM tag_vote"))
        ).scalar_one() == 0
        assert (
            await session.execute(
                text(
                    "SELECT data_type FROM information_schema.columns WHERE table_schema=:schema AND table_name='tag_binding' AND column_name='id'"
                ),
                {"schema": schema},
            )
        ).scalar_one() == "bigint"
        assert (
            await session.execute(
                text(
                    "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_schema=:schema AND constraint_type='FOREIGN KEY'"
                ),
                {"schema": schema},
            )
        ).scalar_one() == 0
        await session.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.asyncio
async def test_http_contract_and_notification_privacy(setup_tags, monkeypatch):
    """验证实际 HTTP 路由、字符串 ID 和站内通知逐条已读权限。"""
    import httpx
    from fastapi import FastAPI
    from api.v1.dependencies.security import get_current_user, require_auth
    from api.v1.routers import tags, notifications

    factory, config, _ = setup_tags
    app = FastAPI()
    app.include_router(tags.router, prefix="/v1")
    app.include_router(notifications.router, prefix="/v1")
    paths = app.openapi()["paths"]
    assert "/v1/tags/stats" in paths
    assert "/v1/tags/manage" not in paths
    assert "post" in paths["/v1/tags"]
    assert "patch" in paths["/v1/tags/{tag_id}"]
    assert not any(path.startswith("/v1/custom-tags") for path in paths)
    current = {"id": "99"}
    app.dependency_overrides[require_auth] = lambda: current
    app.dependency_overrides[get_current_user] = lambda: current
    monkeypatch.setattr(tags, "event_mediator", create_tag_mediator(factory, config))
    monkeypatch.setattr(notifications, "AsyncSessionFactory", factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/v1/tags",
            json={"name": "标准名", "category": 1},
        )
        assert response.status_code == 201
        tag_id = response.json()["id"]
        assert isinstance(tag_id, str)
        second = await client.post("/v1/tags", json={"name": "关联标签", "category": 2})
        other_id = second.json()["id"]
        response = await client.patch(
            f"/v1/tags/{tag_id}", json={"name": "改后标准名", "enabled": False}
        )
        assert response.status_code == 200 and response.json()["enabled"] is False
        response = await client.put(
            f"/v1/tags/{tag_id}/aliases", json={"aliases": ["SearchAlias"]}
        )
        assert response.status_code == 200
        response = await client.get(
            "/v1/tags", params={"q": "SearchAlias", "selectable": "false"}
        )
        assert response.json()["results"][0]["id"] == tag_id
        assert response.json()["total"] == 1
        assert (
            await client.put(f"/v1/tags/{tag_id}/aliases", json={"aliases": []})
        ).status_code == 200
        response = await client.get(
            "/v1/tags", params={"q": "SearchAlias", "selectable": "false"}
        )
        assert response.json() == {"results": [], "total": 0}
        response = await client.post(
            f"/v1/tags/{tag_id}/relations",
            json={"target_tag_id": other_id, "kind": "implies"},
        )
        assert response.status_code == 200
        response = await client.get("/v1/tags/relations")
        assert {
            "source_id": tag_id,
            "target_id": other_id,
            "kind": "implies",
        } in response.json()
        assert (
            await client.delete(f"/v1/tags/{tag_id}/relations/implies/{other_id}")
        ).status_code == 200
        assert (await client.get("/v1/tags/relations")).json() == []
        assert (await client.delete(f"/v1/tags/{tag_id}")).status_code == 200
        response = await client.patch(
            f"/v1/tags/{tag_id}", json={"name": "不得部分写入", "enabled": True}
        )
        assert response.status_code == 409
        response = await client.post(f"/v1/tags/{tag_id}/restore")
        assert response.status_code == 200 and response.json()["enabled"] is True
        assert response.json()["name"] == "改后标准名"
        for body in (
            {},
            {"name": None},
            {"enabled": None},
            {"enabled": 1},
            {"aliases": []},
        ):
            assert (
                await client.patch(f"/v1/tags/{tag_id}", json=body)
            ).status_code == 422
        assert (await client.post("/v1/tags", json={"category": 1})).status_code == 422
        assert (
            await client.post("/v1/tags", json={"name": "无分类"})
        ).status_code == 422
        assert (
            await client.post(f"/v1/tags/{tag_id}/relations", json={"kind": "implies"})
        ).status_code == 422
        assert (
            await client.put(f"/v1/tags/{tag_id}/aliases", json={})
        ).status_code == 422
        current["id"] = "3"
        denied = [
            ("POST", "/v1/tags", {"name": "无权限", "category": 1}),
            ("PATCH", f"/v1/tags/{tag_id}", {"enabled": False}),
            ("DELETE", f"/v1/tags/{tag_id}", None),
            ("POST", f"/v1/tags/{tag_id}/restore", None),
            ("PUT", f"/v1/tags/{tag_id}/aliases", {"aliases": []}),
            (
                "POST",
                f"/v1/tags/{tag_id}/relations",
                {"target_tag_id": other_id, "kind": "implies"},
            ),
            ("DELETE", f"/v1/tags/{tag_id}/relations/implies/{other_id}", None),
        ]
        for method, path, body in denied:
            assert (await client.request(method, path, json=body)).status_code == 403
        response = await client.post(
            "/v1/tags/booklist/1/proposals", json={"tag_id": tag_id}
        )
        assert response.status_code == 200
        assert "applicant_id" not in response.json()
        assert (await client.get("/v1/tags/booklist/1/audit")).status_code == 403
        assert (
            await client.put("/v1/tags/booklist/1/votes/1", json={"vote": 2})
        ).status_code == 422

        async def fallback(proposal):
            return False

        await TagWorker(factory, config).deliver(fallback)
        current["id"] = "1"
        response = await client.get("/v1/notifications")
        assert response.status_code == 200
        # 通知响应沿用项目分页结构。
        data = response.json()
        items = data["results"]
        assert len(items) == 1 and items[0]["type"] == "tag_review"
        notice_id = items[0]["id"]
        assert items[0]["target_type"] == "booklist" and items[0]["thread"] is None
        current["id"] = "3"
        response = await client.post(f"/v1/notifications/{notice_id}/read")
        assert response.json()["marked_read"] == 0
        current["id"] = "1"
        response = await client.post(f"/v1/notifications/{notice_id}/read")
        assert response.json()["marked_read"] == 1


@pytest.mark.asyncio
async def test_pool_source_filter_returns_all_matches(setup_tags):
    """不同来源同名、转换实体及超过百条数据均在筛选后完整返回。"""
    from models import Tag

    factory, _, call = setup_tags
    async with factory() as session, session.begin():
        session.add_all(
            [Tag(name=f"候选{i:03}", source="custom", category=3) for i in range(101)]
        )
        session.add(
            Tag(
                name="候选000",
                source="discord",
            )
        )
        session.add(Tag(name="已转换", source="custom", originated_from_discord=True))
        session.add(Tag(name="已停用", source="custom", category=3, enabled=False))

    statements = []

    def record_statement(_conn, _cursor, statement, _parameters, _context, _many):
        """记录一次完整池请求实际执行的 SQL。"""
        statements.append(statement)

    engine = factory.kw["bind"].sync_engine
    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        custom = await call("pool", source="custom")
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)
    assert len(custom) == 102
    assert len(statements) == 4
    assert not any("count(" in statement.lower() for statement in statements)
    assert all(tag["source"] == "custom" for tag in custom)
    assert any(tag["name"] == "已转换" for tag in custom)
    discord = await call("pool", source="discord")
    assert len(discord) == 1 and discord[0]["name"] == "候选000"
    same_name = await call("pool", q="候选000")
    assert {tag["source"] for tag in same_name} == {"custom", "discord"}
    filtered = await call("pool", source="custom", q="候选000", category=3)
    assert len(filtered) == 1 and filtered[0]["source"] == "custom"
    assert await call("pool", source="custom", q="已停用") == []
    assert len(await call("pool", source="custom", q="已停用", selectable=False)) == 1
