# ruff: noqa: F811
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import discord

import pytest
from sqlalchemy import select

from test_custom_tag_governance import setup_tags, create, attach  # noqa: F401, F811
from core.discord_tag_sync_service import DiscordTagSyncService
from core.tag_binding_repository import TagBindingRepository
from core.thread_repository import ThreadRepository
from dto.events.discord_tags_snapshot import DiscordTagsSnapshot
from models import (
    Tag,
    DiscordTagSource,
    Thread,
    TagBinding,
    TagVote,
    TagAlias,
    TagNotificationTask,
    OperationLog,
)
from search.suggestion_service import SuggestionService
from shared.tag_error import TagError
from shared.time_utils import utc_now
from tag.tag_statistics_service import TagStatisticsService
from api.v1.schemas.tags.tag_stats_request import TagStatsRequest


async def sync(factory, values, channel_id=20, observed=None):
    """将成功的完整快照应用到真实数据库。"""
    async with factory() as session, session.begin():
        await DiscordTagSyncService(session).apply(
            DiscordTagsSnapshot(channel_id, values, observed or utc_now())
        )


@pytest.mark.asyncio
async def test_discord_sync_reports_only_public_pool_changes(setup_tags):
    """相同来源的周期对账不失效缓存，新增与改名会报告标签池变化。"""
    factory, _, _ = setup_tags
    first = utc_now()
    async with factory() as session, session.begin():
        assert await DiscordTagSyncService(session).apply(
            DiscordTagsSnapshot(20, {12345: "原名"}, first)
        )
    async with factory() as session, session.begin():
        assert not await DiscordTagSyncService(session).apply(
            DiscordTagsSnapshot(20, {12345: "原名"}, first + timedelta(seconds=1))
        )
    async with factory() as session, session.begin():
        assert await DiscordTagSyncService(session).apply(
            DiscordTagsSnapshot(20, {12345: "新名"}, first + timedelta(seconds=2))
        )


@pytest.mark.asyncio
async def test_delete_convert_rename_recreate_and_stale_snapshot(setup_tags):
    """删除保留实体和绑定，旧快照不复活实体，同名重建使用新身份。"""
    factory, _, call = setup_tags
    await sync(factory, {12345: "原名"})
    async with factory() as session, session.begin():
        tag = (
            await session.execute(
                select(Tag)
                .join(DiscordTagSource, DiscordTagSource.tag_id == Tag.id)
                .where(DiscordTagSource.discord_tag_id == 12345)
            )
        ).scalar_one()
        tag_id = tag.id
        await ThreadRepository(session).add_or_update_thread_with_tags(
            {
                "thread_id": 100,
                "channel_id": 20,
                "guild_id": 10,
                "author_id": 1,
                "title": "测试",
            },
            [tag],
        )
    native = await call("read", target_type="thread", target_id=100)
    assert native["tags"][0]["binding_source"] == "discord_sync"
    async with factory() as session:
        binding = (await session.execute(select(TagBinding))).scalar_one()
        binding_id = binding.id
    with pytest.raises(TagError, match="不可投票"):
        await call(
            "vote", target_type="thread", target_id=100, binding_id=binding_id, vote=1
        )
    with pytest.raises(TagError):
        await attach(call, [tag_id])
    booklist = await attach(call, [tag_id], kind="booklist", tid=1)
    assert booklist["tags"][0]["source"] == "discord"
    assert booklist["tags"][0]["binding_source"] == "local"
    await sync(factory, {12345: "新名"})
    assert (await call("read", target_type="booklist", target_id=1))["tags"][0][
        "name"
    ] == "原名"
    older = utc_now() - timedelta(hours=1)
    await sync(factory, {})
    await sync(factory, {})
    await sync(factory, {12345: "旧快照"}, observed=older)
    converted = await call("read", target_type="thread", target_id=100)
    assert converted["tags"][0]["id"] != str(tag_id)
    assert converted["tags"][0]["name"] == "新名"
    assert converted["tags"][0]["source"] == "custom"
    assert converted["tags"][0]["category"] is None
    assert converted["tags"][0]["binding_source"] == "local"
    assert converted["version"] != native["version"]
    async with factory() as session, session.begin():
        await ThreadRepository(session).add_or_update_thread_with_tags(
            {
                "thread_id": 100,
                "channel_id": 20,
                "guild_id": 10,
                "author_id": 1,
                "title": "测试",
            },
            [],
        )
        assert (
            len(list((await session.execute(select(TagNotificationTask))).scalars()))
            == 2
        )
    assert (await call("read", target_type="thread", target_id=100))["tags"]
    await sync(factory, {67890: "新名"})
    async with factory() as session:
        tags = list((await session.execute(select(Tag))).scalars())
        assert len(tags) == 3
        assert {tag.id for tag in tags} != {tag_id}


@pytest.mark.asyncio
async def test_classification_conflict_is_durable_and_admin_only(setup_tags):
    """分类失败不改名不合并，冲突提醒不随失败事务回滚。"""
    factory, _, call = setup_tags
    await create(call, name="冲突")
    await sync(factory, {1: "冲突"})
    await sync(factory, {})
    async with factory() as session:
        tag_id = (
            await session.execute(
                select(DiscordTagSource.tag_id).where(
                    DiscordTagSource.discord_tag_id == 1
                )
            )
        ).scalar_one()
    with pytest.raises(TagError) as forbidden:
        await call("manage", 2, operation="classify", tag_id=tag_id, category=3)
    assert forbidden.value.status == 403
    with pytest.raises(TagError):
        await call("manage", 99, operation="classify", tag_id=tag_id, category=3)
    async with factory() as session:
        assert (await session.get(Tag, tag_id)).category is None
        assert (
            await session.execute(
                select(TagNotificationTask).where(
                    TagNotificationTask.kind == "conflict"
                )
            )
        ).scalar_one()
    result = await call("manage", 99, operation="classify", tag_id=tag_id, category=4)
    assert result["category"] == 4
    with pytest.raises(TagError):
        await call("manage", 99, operation="classify", tag_id=tag_id, category=5)


@pytest.mark.asyncio
async def test_suggestions_name_search_statistics_and_cleanup(setup_tags):
    """跨来源同名检索、分类分组及别名联想均使用有效绑定。"""
    factory, _, call = setup_tags
    a = await create(call, name="同名")
    b = await call("manage", 99, operation="create", name="同名", category=4)
    await sync(factory, {1: "同名"})
    await sync(factory, {2: "同名"}, channel_id=30)
    async with factory() as session, session.begin():
        native = list(
            (
                await session.execute(select(Tag).where(Tag.source == "discord"))
            ).scalars()
        )
        await ThreadRepository(session).add_or_update_thread_with_tags(
            {
                "thread_id": 100,
                "channel_id": 20,
                "guild_id": 10,
                "author_id": 1,
                "title": "测试",
            },
            native,
        )
        session.add(TagAlias(tag_id=int(a["id"]), name="Alice"))
    await attach(call, [a["id"], b["id"]])
    async with factory() as session:
        assert list(
            (
                await session.execute(
                    select(Thread.thread_id).where(Thread.tags.any(Tag.name == "同名"))
                )
            ).scalars()
        ) == [100]
        suggestions = await SuggestionService(session).get_suggestions("Alice")
        assert [t.name for t in suggestions.tags] == ["同名"]
        cache = SimpleNamespace(
            indexed_channels={}, bot=SimpleNamespace(get_channel=lambda _: None)
        )
        stats = await TagStatisticsService(session, cache, {}).aggregate_tag_stats(
            TagStatsRequest(include_virtual=False)
        )
        assert {(i.source, i.category, i.total_thread_count) for i in stats.items} == {
            ("discord", None, 1),
            ("custom", 3, 1),
            ("custom", 4, 1),
        }
        assert len(next(i for i in stats.items if i.source == "discord").tag_ids) == 1
    await call("manage", 99, operation="disable", tag_id=a["id"])
    async with factory() as session:
        assert not (await SuggestionService(session).get_suggestions("Alice")).tags
        assert (
            await session.execute(
                select(Thread).where(Thread.tags.any(Tag.id == int(a["id"])))
            )
        ).scalar_one()
    await call("manage", 99, operation="delete", tag_id=a["id"])
    async with factory() as session, session.begin():
        assert (
            not (
                await session.execute(
                    select(Thread).where(Thread.tags.any(Tag.id == int(a["id"])))
                )
            )
            .scalars()
            .all()
        )
        await TagBindingRepository(session).delete_targets("thread", [100])
        assert not (await session.execute(select(TagBinding))).scalars().all()
        assert not (await session.execute(select(TagVote))).scalars().all()
        assert (await session.execute(select(OperationLog))).scalars().all()


@pytest.mark.asyncio
async def test_abyss_suggestions_and_statistics_visibility(setup_tags):
    """深渊向 TAG 仅在授权的发现型联想和统计中出现。"""
    factory, _, call = setup_tags
    abyss = await create(
        call, name="深渊候选", aliases=["AbyssAlias"], is_abyss=True
    )
    await attach(call, [abyss["id"]])
    async with factory() as session:
        hidden = await SuggestionService(session).get_suggestions("AbyssAlias")
        visible = await SuggestionService(session).get_suggestions(
            "AbyssAlias", include_abyss_tags=True
        )
        assert hidden.tags == []
        assert [tag.name for tag in visible.tags] == ["深渊候选"]

        cache = SimpleNamespace(
            indexed_channels={}, bot=SimpleNamespace(get_channel=lambda _: None)
        )
        hidden_stats = await TagStatisticsService(
            session, cache, {}
        ).aggregate_tag_stats(TagStatsRequest(include_virtual=False))
        visible_stats = await TagStatisticsService(
            session, cache, {}
        ).aggregate_tag_stats(
            TagStatsRequest(include_virtual=False), can_view_abyss=True
        )
        assert hidden_stats.items == []
        assert len(visible_stats.items) == 1
        assert visible_stats.items[0].is_abyss is True


@pytest.mark.asyncio
async def test_failed_fetch_is_not_deletion_and_message_routes(setup_tags):
    """读取失败不发布删除事件，作者私信链接直达详情。"""
    from core.sync_service import SyncService
    from tag.cog import TagCog

    factory, config, _ = setup_tags
    bot = SimpleNamespace(
        fetch_channel=AsyncMock(side_effect=PermissionError()),
        event_mediator=SimpleNamespace(publish=AsyncMock()),
    )
    with pytest.raises(PermissionError):
        await SyncService(bot, factory).pre_sync_forum_tags(SimpleNamespace(id=20))
    bot.event_mediator.publish.assert_not_awaited()
    user = SimpleNamespace(send=AsyncMock())
    bot = SimpleNamespace(get_user=lambda _: user)
    cog = TagCog(
        bot, factory, {**config, "auth": {"frontend_url": "https://example.test/"}}
    )
    for kind, path in [("thread", "threads"), ("booklist", "booklists")]:
        await cog.send_notice(
            SimpleNamespace(id=9, owner_id=1, target_type=kind, target_id=123)
        )
        assert f"https://example.test/{path}/123" in user.send.call_args.args[0]


@pytest.mark.asyncio
async def test_reconstructed_classification_component_checks_current_actor(setup_tags):
    """从消息组件恢复后重新检查操作者权限，不依赖创建消息时的身份。"""
    import re
    from tag.tag_category_select import TagCategorySelect
    from tag.tag_runtime import create_tag_mediator

    factory, config, _ = setup_tags
    await sync(factory, {12: "待分类"})
    await sync(factory, {})
    async with factory() as session:
        tag_id = (await session.execute(select(Tag.id))).scalar_one()
    mediator = create_tag_mediator(factory, config)
    interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        user=SimpleNamespace(id=2),
        message=SimpleNamespace(edit=AsyncMock()),
        client=SimpleNamespace(get_cog=lambda _: SimpleNamespace(mediator=mediator)),
    )
    match = re.match(r"tag_classify:(?P<tag_id>[0-9]+)", f"tag_classify:{tag_id}")
    component = await TagCategorySelect.from_custom_id(interaction, None, match)
    component.item._values = ["3"]
    await component.callback(interaction)
    async with factory() as session:
        assert (await session.get(Tag, tag_id)).category is None
    interaction.message.edit.assert_not_awaited()
    interaction.user.id = 99
    await component.callback(interaction)
    async with factory() as session:
        assert (await session.get(Tag, tag_id)).category == 3
    interaction.message.edit.assert_awaited_once_with(view=None)


@pytest.mark.asyncio
async def test_thread_event_before_channel_delete_preserves_binding(
    setup_tags, monkeypatch
):
    """帖子更新先到达时先核对完整频道，再决定移除还是转成本地绑定。"""
    from core.sync_service import SyncService

    factory, _, call = setup_tags
    await sync(factory, {12: "保留"})
    async with factory() as session, session.begin():
        tag = (await session.execute(select(Tag))).scalar_one()
        await ThreadRepository(session).add_or_update_thread_with_tags(
            {
                "thread_id": 100,
                "channel_id": 20,
                "guild_id": 10,
                "author_id": 1,
                "title": "测试",
            },
            [tag],
        )
    service = SyncService(SimpleNamespace(), factory)
    monkeypatch.setattr(
        service,
        "_parse_thread_data",
        AsyncMock(
            return_value={
                "thread_id": 100,
                "channel_id": 20,
                "guild_id": 10,
                "author_id": 1,
                "title": "测试",
            }
        ),
    )

    async def fresh_snapshot(channel):
        await sync(factory, {})

    monkeypatch.setattr(service, "pre_sync_forum_tags", fresh_snapshot)
    monkeypatch.setattr(service, "_auto_follow_on_first_detect", AsyncMock())
    thread = Mock(spec=discord.Thread, id=100, parent_id=20, applied_tags=[])
    result = await service.sync_thread(thread)
    assert result.success
    current = await call("read", target_type="thread", target_id=100)
    assert current["tags"][0]["binding_source"] == "local"
