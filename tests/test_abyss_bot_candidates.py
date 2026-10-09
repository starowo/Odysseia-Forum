# ruff: noqa: F811
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from test_custom_tag_governance import attach, create, setup_tags  # noqa: F401
from core.tag_repository import TagRepository
from core.thread_repository import ThreadRepository
from dto.preferences import UserSearchPreferencesDTO
from preferences.views.tag_preferences_view import TagPreferencesView
from search.cog import Search
from shared.abyss_tag_visibility import can_discord_user_view_abyss_tags
from shared.views.tag_select import TagSelect


def test_bot_admin_without_abyss_role_does_not_gain_candidate_visibility():
    """BOT 管理员身份不替代主服务器的深渊身份组。"""
    member = SimpleNamespace(id=99, roles=[SimpleNamespace(id=10)])
    guild = SimpleNamespace(get_member=lambda user_id: member if user_id == 99 else None)
    bot = SimpleNamespace(get_guild=lambda guild_id: guild if guild_id == 1 else None)
    config = {"required_role_id": 20}

    assert not can_discord_user_view_abyss_tags(bot, 99, 1, config)
    member.roles.append(SimpleNamespace(id=20))
    assert can_discord_user_view_abyss_tags(bot, 99, 1, config)


@pytest.mark.asyncio
async def test_global_and_channel_candidates_exclude_custom_and_filter_abyss(
    setup_tags,
):
    """全局和频道候选只含原生及虚拟 TAG，并按深渊身份过滤。"""
    factory, _, call = setup_tags
    custom_normal = await create(call, name="自定义正常")
    custom_abyss = await create(call, name="自定义深渊", is_abyss=True)

    async with factory() as session, session.begin():
        native_tags = await TagRepository(session).get_or_create_tags(
            {101: "原生正常", 102: "原生深渊"}, channel_id=20
        )
        next(tag for tag in native_tags if tag.name == "原生深渊").is_abyss = True
        await ThreadRepository(session).add_or_update_thread_with_tags(
            {
                "thread_id": 100,
                "channel_id": 20,
                "guild_id": 10,
                "author_id": 1,
                "title": "测试",
            },
            native_tags,
        )
    await attach(call, [custom_normal["id"], custom_abyss["id"]])

    cog = Search.__new__(Search)
    cog.session_factory = factory
    cog.tag_service = SimpleNamespace()
    cog.channel_mappings_utils = SimpleNamespace(
        channel_mappings={20: [{"tag_name": "虚拟分区"}]}
    )
    cog.cache_service = SimpleNamespace(
        indexed_channels={
            20: SimpleNamespace(
                available_tags=[
                    SimpleNamespace(name="原生正常"),
                    SimpleNamespace(name="原生深渊"),
                ]
            )
        }
    )

    global_hidden = await cog.get_merged_tags_separated([], include_abyss=False)
    global_visible = await cog.get_merged_tags_separated([], include_abyss=True)
    channel_hidden = await cog.get_merged_tags_separated([20], include_abyss=False)
    channel_visible = await cog.get_merged_tags_separated([20], include_abyss=True)

    assert global_hidden.all_tags == ["虚拟分区", "原生正常"]
    assert global_visible.all_tags == ["虚拟分区", "原生正常", "原生深渊"]
    assert channel_hidden.all_tags == ["虚拟分区", "原生正常"]
    assert channel_visible.all_tags == ["虚拟分区", "原生正常", "原生深渊"]
    assert "自定义正常" not in global_visible.all_tags
    assert "自定义深渊" not in global_visible.all_tags

    async with factory() as session:
        candidates = await TagRepository(session).get_candidate_names(
            source="discord", include_abyss=False
        )
        assert candidates == ["原生正常"]
        author_tags = await cog.get_tags_for_author(1, include_abyss=False)
        assert {tag.name for tag in author_tags} == {"原生正常", "自定义正常"}


@pytest.mark.asyncio
async def test_saved_custom_preferences_stay_visible_and_survive_dropdown_changes():
    """候选外的已保存自定义 TAG 仍显示在占位和摘要并随修改保留。"""
    preferences = UserSearchPreferencesDTO(
        user_id=1,
        include_tags=["原生正常", "自定义正选"],
        exclude_tags=["自定义反选"],
    )
    view = TagPreferencesView(
        SimpleNamespace(),
        SimpleNamespace(),
        SimpleNamespace(),
        preferences,
        ["原生正常", "原生其他"],
    )
    include_select = view.children[0]
    exclude_select = view.children[1]

    assert {option.value for option in include_select.options} == {
        "原生正常",
        "原生其他",
    }
    assert "自定义正选" not in {option.value for option in include_select.options}
    assert "自定义正选" in include_select.placeholder
    assert "自定义反选" in exclude_select.placeholder
    embed_values = [field.value for field in view.build_embed().fields]
    assert any("自定义正选" in value for value in embed_values)
    assert any("自定义反选" in value for value in embed_values)

    callback = AsyncMock()
    select = TagSelect(
        all_tags=["原生正常", "原生其他"],
        selected_tags={"原生正常", "自定义正选"},
        page=0,
        tags_per_page=25,
        placeholder_prefix="正选",
        custom_id="test_saved_custom_preferences",
        on_change_callback=callback,
    )
    select._values = ["原生其他"]
    interaction = SimpleNamespace()
    await select.callback(interaction)
    callback.assert_awaited_once_with(
        interaction, {"原生其他", "自定义正选"}
    )
