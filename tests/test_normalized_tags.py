# ruff: noqa: F811
from datetime import timedelta

import pytest
from sqlalchemy import select

from test_custom_tag_governance import setup_tags, create, attach  # noqa: F401
from core.discord_tag_sync_service import DiscordTagSyncService
from core.thread_repository import ThreadRepository
from core.tag_query import require_current_tag_ids
from dto.events.discord_tags_snapshot import DiscordTagsSnapshot
from models import (
    Tag,
    DiscordTagSource,
    DiscordTagSyncState,
    TagBinding,
    TagVote,
    TagProposal,
    TagProposalBlock,
    TagNotificationTask,
    OperationLog,
)
from shared.tag_error import TagError
from shared.time_utils import utc_now


@pytest.mark.asyncio
async def test_source_swap_and_raw_name_preservation(setup_tags):
    """一次频道快照交换名称时绑定随来源切换，维护分类不规范化 DC 名称。"""
    factory, _, call = setup_tags
    await sync(factory, 20, {11: " A ", 12: "B"})
    await native(factory)
    before = await call("read", target_type="thread", target_id=100)
    ids = {t["name"]: t["id"] for t in before["tags"]}
    await call("manage", 99, operation="update", tag_id=ids[" A "], category=3)
    pool = await call("pool", source="discord")
    assert {t["name"] for t in pool} == {" A ", "B"}
    await sync(factory, 20, {11: "B", 12: " A "})
    after = await call("read", target_type="thread", target_id=100)
    assert {t["id"] for t in after["tags"]} == set(ids.values())
    assert after["version"] != before["version"]
    async with factory() as session:
        sources = {
            s.discord_tag_id: s
            for s in (await session.execute(select(DiscordTagSource))).scalars()
        }
        assert sources[11].tag_id == int(ids["B"])
        assert sources[12].tag_id == int(ids[" A "])
        history = list(
            (
                await session.execute(
                    select(TagBinding).where(TagBinding.ended_at.is_not(None))
                )
            ).scalars()
        )
        assert len(history) == 2


@pytest.mark.asyncio
async def test_discord_tag_can_be_marked_abyss_without_sync_overwrite(setup_tags):
    """DC 概念可手工切换方向，后续频道同步不会按频道自动覆盖。"""
    factory, _, call = setup_tags
    await sync(factory, 20, {11: "原生深渊"})
    concept = (await call("pool", source="discord"))[0]

    updated = await call(
        "manage",
        99,
        operation="update",
        tag_id=concept["id"],
        is_abyss=True,
    )
    assert updated["source"] == "discord"
    assert updated["is_abyss"] is True
    assert await call("pool", source="discord") == []
    assert (await call("pool", source="discord", _can_view_abyss=True))[0][
        "is_abyss"
    ] is True

    await sync(factory, 20, {11: "原生深渊"})
    async with factory() as session:
        tag = (await session.execute(select(Tag))).scalar_one()
        assert tag.is_abyss is True
        log = (
            await session.execute(
                select(OperationLog)
                .where(OperationLog.type == "tag.pool.update")
                .order_by(OperationLog.id.desc())
            )
        ).scalars().first()
        assert log.detail["before"]["is_abyss"] is False
        assert log.detail["after"]["is_abyss"] is True


@pytest.mark.asyncio
async def test_normalized_http_snapshot_and_merge(setup_tags, monkeypatch):
    """真实事件链路的 HTTP 响应区分绑定权限，旧合并 ID 返回刷新错误。"""
    import httpx
    from fastapi import FastAPI
    from api.v1.dependencies.security import require_auth
    from api.v1.routers import tags
    from tag.tag_runtime import create_tag_mediator

    factory, config, call = setup_tags
    custom = await create(call, name="统一", is_abyss=True)
    await sync(factory, 20, {9007199254740993: "统一"})
    await sync(factory, 30, {9007199254740994: "统一"})
    concept = (await call("pool", source="discord"))[0]
    await attach(call, [concept["id"]], kind="booklist", tid=1)
    await native(factory)
    app = FastAPI()
    app.include_router(tags.router, prefix="/v1")
    app.dependency_overrides[require_auth] = lambda: {"id": "99"}
    monkeypatch.setattr(tags, "event_mediator", create_tag_mediator(factory, config))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        thread = (await client.get("/v1/tags/thread/100")).json()["tags"][0]
        book = (await client.get("/v1/tags/booklist/1")).json()["tags"][0]
        assert thread["readonly"] and thread["binding_source"] == "discord_sync"
        assert book["readonly"] is False and book["source"] == "discord"
        assert {s["discord_tag_id"] for s in book["discord_sources"]} == {
            "9007199254740993",
            "9007199254740994",
        }
        assert "my_vote" not in thread and book["my_vote"] == 0
        preview = await client.get(
            f"/v1/tags/{custom['id']}/merge-preview",
            params={"target_tag_id": concept["id"]},
        )
        assert preview.status_code == 200
        assert preview.json()["source_is_abyss"] is True
        assert preview.json()["target_is_abyss"] is False
        response = await client.post(
            f"/v1/tags/{custom['id']}/merge",
            json={"target_tag_id": concept["id"], "version": preview.json()["version"]},
        )
        assert response.status_code == 200 and response.json()["id"] == concept["id"]
        assert response.json()["is_abyss"] is False
        old = await client.post(f"/v1/tags/{custom['id']}/restore")
        assert old.status_code == 409 and old.json()["detail"]["code"] == "tags_changed"


async def sync(factory, channel, tags, observed=None):
    """执行真实完整频道快照。"""
    async with factory() as session, session.begin():
        await DiscordTagSyncService(session).apply(
            DiscordTagsSnapshot(channel, tags, observed or utc_now())
        )


async def native(factory, thread=100, channel=20):
    """按来源频道选择标准概念同步帖子。"""
    async with factory() as session, session.begin():
        tags = list(
            (
                await session.execute(
                    select(Tag)
                    .join(DiscordTagSource, DiscordTagSource.tag_id == Tag.id)
                    .where(
                        DiscordTagSource.channel_id == channel,
                        DiscordTagSource.deleted_at.is_(None),
                    )
                )
            ).scalars()
        )
        await ThreadRepository(session).add_or_update_thread_with_tags(
            {
                "thread_id": thread,
                "channel_id": channel,
                "guild_id": 10,
                "author_id": 1,
                "title": "测试",
            },
            tags,
        )


@pytest.mark.asyncio
async def test_channels_rename_delete_and_checkpoint(setup_tags):
    """同名归一、改名不影响书单、来源删除及空快照不被旧事件覆盖。"""
    factory, _, call = setup_tags
    await sync(factory, 20, {111: "纯爱"})
    await sync(factory, 30, {222: "纯爱"})
    pool = await call("pool", source="discord")
    assert len(pool) == 1 and len(pool[0]["discord_sources"]) == 2
    old_id = int(pool[0]["id"])
    await native(factory)
    await attach(call, [old_id], kind="booklist", tid=1)
    locked = await call("read", target_type="thread", target_id=100)
    assert locked["tags"][0]["readonly"]
    await sync(factory, 20, {111: "恋爱"})
    assert (await call("read", target_type="booklist", target_id=1))["tags"][0][
        "name"
    ] == "纯爱"
    renamed = await call("read", target_type="thread", target_id=100)
    assert renamed["tags"][0]["name"] == "恋爱"
    assert renamed["version"] != locked["version"]
    stale = utc_now() - timedelta(hours=1)
    await sync(factory, 20, {})
    await sync(factory, 20, {111: "过期"}, stale)
    local = await call("read", target_type="thread", target_id=100)
    assert local["tags"][0]["source"] == "custom" and not local["tags"][0]["readonly"]
    assert (await call("read", target_type="booklist", target_id=1))["tags"][0][
        "source"
    ] == "discord"
    await sync(factory, 30, {})
    assert (await call("read", target_type="booklist", target_id=1))["tags"][0][
        "source"
    ] == "custom"
    await sync(factory, 20, {333: "恋爱"})
    assert len(await call("pool", q="恋爱")) == 2
    async with factory() as session:
        assert await session.get(DiscordTagSyncState, 20)
        assert (
            len(
                list(
                    (
                        await session.execute(
                            select(TagBinding).where(TagBinding.target_type == "thread")
                        )
                    ).scalars()
                )
            )
            == 2
        )


@pytest.mark.asyncio
async def test_takeover_delete_conflict_and_admin_controls(setup_tags):
    """同概念本地转 DC 新轮次、分类冲突降级以及 DC 池维护权限。"""
    factory, _, call = setup_tags
    await sync(factory, 20, {111: "纯爱"})
    dc = (await call("pool", source="discord"))[0]
    tag_id = int(dc["id"])
    await call(
        "manage", 99, operation="update", tag_id=tag_id, category=3, aliases=["love"]
    )
    with pytest.raises(TagError):
        await call("manage", 99, operation="update", tag_id=tag_id, name="别名")
    with pytest.raises(TagError):
        await call("manage", 99, operation="delete", tag_id=tag_id)
    await create(call, name="纯爱")
    async with factory() as session, session.begin():
        local = TagBinding(
            target_type="thread", target_id=100, tag_id=tag_id, upvotes=1
        )
        session.add(local)
        await session.flush()
        old_id = local.id
        session.add(TagVote(binding_id=old_id, user_id=1, vote=1))
    await native(factory)
    async with factory() as session:
        active = (
            await session.execute(
                select(TagBinding).where(
                    TagBinding.ended_at.is_(None), TagBinding.target_type == "thread"
                )
            )
        ).scalar_one()
        assert active.id != old_id and active.upvotes == 0
        assert (await session.get(TagBinding, old_id)).end_reason == "discord_takeover"
        assert await session.get(TagVote, (old_id, 1))
    await sync(factory, 20, {})
    async with factory() as session:
        converted = await session.get(Tag, tag_id)
        assert converted.source == "custom" and converted.category is None
        assert list(
            (
                await session.execute(
                    select(OperationLog).where(OperationLog.type == "tag.pool.convert")
                )
            ).scalars()
        )


@pytest.mark.asyncio
async def test_merge_preserves_rounds_blocks_proposals_and_refresh(setup_tags):
    """合并不合票、继承限制、结束旧申请，旧 ID 明确提示刷新。"""
    factory, _, call = setup_tags
    old = int((await create(call, name="纯爱", aliases=["别名"]))["id"])
    await sync(factory, 20, {111: "纯爱"})
    target = int((await call("pool", source="discord"))[0]["id"])
    await attach(call, [old, target], kind="booklist", tid=1)
    async with factory() as session, session.begin():
        rounds = {
            b.tag_id: b for b in (await session.execute(select(TagBinding))).scalars()
        }
        target_binding = rounds[target].id
        rounds[target].upvotes = 1
        session.add(TagVote(binding_id=target_binding, user_id=1, vote=1))
        session.add(TagProposalBlock(target_type="thread", target_id=100, tag_id=old))
        proposal = TagProposal(
            target_type="thread",
            target_id=100,
            tag_id=old,
            applicant_id=3,
            owner_id=1,
            due_at=utc_now() + timedelta(days=7),
        )
        session.add(proposal)
        await session.flush()
        session.add(TagNotificationTask(proposal_id=proposal.id))
    with pytest.raises(TagError):
        await call("merge", 2, tag_id=old, target_tag_id=target, preview=True)
    preview = await call("merge", 99, tag_id=old, target_tag_id=target, preview=True)
    assert preview["can_merge"] and preview["binding_count"] == 1
    with pytest.raises(TagError):
        await call("merge", 99, tag_id=old, target_tag_id=target, version="stale")
    result = await call(
        "merge", 99, tag_id=old, target_tag_id=target, version=preview["version"]
    )
    assert result["id"] == str(target)
    snapshot = await call("read", target_type="booklist", target_id=1)
    assert len(snapshot["tags"]) == 1 and snapshot["tags"][0]["binding_id"] == str(
        target_binding
    )
    assert snapshot["tags"][0]["upvotes"] == 1
    async with factory() as session:
        assert (await session.get(Tag, old)).deleted_at
        assert await session.get(TagProposalBlock, ("thread", 100, target))
        assert (
            await session.execute(select(TagProposal))
        ).scalar_one().status == "failed"
        assert (
            await session.execute(
                select(TagNotificationTask).where(
                    TagNotificationTask.proposal_id.is_not(None)
                )
            )
        ).scalar_one().status == "cancelled"
        with pytest.raises(TagError, match="刷新"):
            await require_current_tag_ids(session, [old])
    with pytest.raises(TagError):
        await attach(call, [old], kind="booklist", tid=1)
    with pytest.raises(TagError):
        await call("manage", 99, operation="restore", tag_id=old)


@pytest.mark.asyncio
async def test_merge_graph_conflict_and_binding_warnings(setup_tags):
    """关系自环阻断合并；同步导致互斥时不自动删除本地绑定。"""
    factory, _, call = setup_tags
    old = int((await create(call, name="同名"))["id"])
    await sync(factory, 20, {1: "同名"})
    target = int((await call("pool", source="discord"))[0]["id"])
    await call(
        "manage",
        99,
        operation="add_relation",
        tag_id=old,
        target_tag_id=target,
        kind="excludes",
    )
    preview = await call("merge", 99, tag_id=old, target_tag_id=target, preview=True)
    assert not preview["can_merge"]
    with pytest.raises(TagError):
        await call(
            "merge", 99, tag_id=old, target_tag_id=target, version=preview["version"]
        )
    await attach(call, [old])
    await native(factory)
    current = await call("read", target_type="thread", target_id=100)
    assert len(current["tags"]) == 2 and current["conflicting_pairs"]
    await attach(call, [])
    assert len((await call("read", target_type="thread", target_id=100))["tags"]) == 1
