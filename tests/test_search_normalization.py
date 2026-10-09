"""固定 OpenCC 词典、搜索语法及在线索引更新的 PostgreSQL 回归测试。"""

import hashlib
import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from core.banner_title_filter_repository import BannerTitleFilterRepository
from core.booklist_repository import BooklistRepository
from core.thread_repository import ThreadRepository
from models import Booklist, Thread
from shared.enum import CacheKeys
from shared.search_normalization import (
    SEARCH_CONVERSION_CONFIGS,
    SEARCH_NORMALIZATION_VERSION,
    normalize_search_text,
)


@pytest.mark.parametrize(
    "original,expected",
    [
        ("繁體中文與簡體中文", "繁体中文与简体中文"),
        ("軟體", "软件"),
        ("软体", "软件"),
        ("软件", "软件"),
        ("滑鼠", "鼠标"),
        ("鼠標", "鼠标"),
        ("鼠标", "鼠标"),
        ("記憶體", "内存"),
        ("记忆体", "内存"),
        ("内存", "内存"),
        ("記憶體模組", "内存条"),
        ("记忆体模组", "内存条"),
        ("寬頻", "宽带"),
        ("宽频", "宽带"),
        ("游標", "光标"),
        ("基斯杜化·路蘭", "克里斯托弗·诺兰"),
        ("軟體動物", "软体动物"),
        ("软体动物", "软体动物"),
        ("的士 雪櫃", "的士 雪柜"),
        (
            "軟體 软体 記憶體模組 滑鼠 寬頻 English 🈲",
            "软件 软件 内存条 鼠标 宽带 English 🈲",
        ),
        ('"軟體"，寬頻/滑鼠', '"软件"，宽带/鼠标'),
        ("", ""),
    ],
)
def test_normalization_dictionary_boundary(original, expected):
    """繁简、混合地区词及词组例外严格遵循固定版本词典。"""
    assert normalize_search_text(original) == expected
    assert normalize_search_text(expected) == expected


def test_conversion_order():
    """两次字形统一必须分别位于香港和台湾词典前。"""
    assert SEARCH_CONVERSION_CONFIGS == (
        "s2t.json",
        "hk2sp.json",
        "s2t.json",
        "tw2sp.json",
    )
    # 此词必须先由香港词典处理，台湾词典先处理会破坏香港长词匹配。
    assert normalize_search_text("记忆体模组 軟體 滑鼠") == "内存条 软件 鼠标"


@pytest_asyncio.fixture
async def regional_session(db_session_factory):
    """同时填充帖子和书单，保留原文供显示验证。"""
    texts = [
        ("軟體指南", "滑鼠 記憶體 English 😺"),
        ("软件教程", "鼠标 内存"),
        ("寬頻 記憶體模組", None),
        ("軟體動物", None),
        ("軟體 禁", None),
        ("軟體 🈲", None),
        ("软件 宽带", None),
        ("軟體 記憶體", None),
    ]
    async with db_session_factory() as session:
        for index, (title, body) in enumerate(texts, start=1):
            session.add(
                Thread(
                    id=index,
                    thread_id=100 + index,
                    channel_id=1,
                    author_id=1,
                    title=title,
                    first_message_excerpt=body,
                )
            )
            session.add(Booklist(id=index, owner_id=1, title=title, description=body))
        await session.commit()
        yield session


async def matched_ids(
    session, table, keywords=None, exclude=None, markers=None, redis=None
):
    """执行真实仓储生成的 FTS 条件并返回主键。"""
    if table == "thread":
        model = Thread
        result = await ThreadRepository(session).get_fts_matched_thread_ids(
            keywords, exclude, markers, redis
        )
    else:
        model = Booklist
        result = await BooklistRepository(session).get_fts_matched_booklist_ids(
            keywords, exclude, redis
        )
    query = select(model.id).where(*result.include_conditions)
    if result.has_exclude:
        query = query.where(~result.exclude_condition)
    return set((await session.execute(query)).scalars())


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["thread", "booklist"])
@pytest.mark.parametrize(
    "keywords,expected",
    [
        ("軟體", {1, 2, 5, 6, 7, 8}),
        ("软体", {1, 2, 5, 6, 7, 8}),
        ("软件", {1, 2, 5, 6, 7, 8}),
        ('"軟體"', {1, 5, 6, 7, 8}),
        ("滑鼠", {1, 2}),
        ("鼠标", {1, 2}),
        ("記憶體模組", {3}),
        ("记忆体模组", {3}),
        ("内存条", {3}),
        ("寬頻", {3, 7}),
        ("宽频", {3, 7}),
        ("宽带", {3, 7}),
        ("軟體/寬頻，滑鼠/記憶體模組", {1, 2, 3}),
        ("软体动物", {4}),
        ("軟體動物", {4}),
        ("ENGLISH", {1}),
        ("😺", {1}),
    ],
)
async def test_regional_search_syntax(regional_session, table, keywords, expected):
    """新增索引对双向查询、引号、AND/OR、英文和 emoji 保持兼容。"""
    assert await matched_ids(regional_session, table, keywords) == expected
    model = Thread if table == "thread" else Booklist
    row = await regional_session.get(model, 1)
    assert row.title == "軟體指南"


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["thread", "booklist"])
async def test_regional_exclusion_and_default_exemption(regional_session, table):
    """地区用语反选与现有禁字和 emoji 豁免共同生效。"""
    assert await matched_ids(regional_session, table, exclude="软体") == {3, 4, 5, 6}


@pytest.mark.asyncio
async def test_regional_text_markers(regional_session):
    """简体化地区豁免词按索引的词形匹配，同时区分禁用豁免。"""
    assert await matched_ids(
        regional_session, "thread", exclude="軟體", markers=["记忆体"]
    ) == {1, 3, 4, 8}
    assert await matched_ids(
        regional_session, "thread", exclude="软件", markers=[]
    ) == {3, 4}


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["thread", "booklist"])
async def test_online_title_and_body_edits(regional_session, table):
    """标题和正文编辑各自触发新索引规则，显示内容保持原文。"""
    model = Thread if table == "thread" else Booklist
    body_field = "first_message_excerpt" if table == "thread" else "description"
    row = await regional_session.get(model, 1)
    row.title = "遊戲合集"
    setattr(row, body_field, "寬頻")
    await regional_session.commit()
    assert 1 in await matched_ids(regional_session, table, "宽带")
    assert 1 not in await matched_ids(regional_session, table, "软件")
    row = await regional_session.get(model, 1)
    setattr(row, body_field, "軟體")
    await regional_session.commit()
    assert 1 in await matched_ids(regional_session, table, "软体")
    await regional_session.refresh(row)
    assert row.title == "遊戲合集"
    assert getattr(row, body_field) == "軟體"


@pytest.mark.asyncio
async def test_banner_regional_exclusion_and_markers(regional_session):
    """Banner 标题快照使用同一索引和查询规范化规则。"""
    titles = {
        1: "軟體",
        2: "软件 禁",
        3: "軟體 記憶體",
        4: "寬頻 記憶體模組",
        5: "軟體動物",
    }
    repo = BannerTitleFilterRepository(regional_session)
    assert await repo.get_excluded_ids(titles, "软体", ["禁"]) == {1, 3}
    assert await repo.get_excluded_ids(titles, "软件", ["记忆体"]) == {1, 2}
    assert await repo.get_excluded_ids(titles, "内存条", []) == {4}
    assert titles[1] == "軟體"


@pytest.mark.asyncio
async def test_real_redis_rule_isolation_and_regional_cache_hit(
    regional_session, redis_client
):
    """旧规则缓存被隔离，地区等价查询可复用新规则缓存。"""
    old_key = CacheKeys.FTS_TSQUERY_RESULT.format(
        prefix="软件", hash=hashlib.md5("软件||".encode()).hexdigest()
    )
    proxy = AsyncMock()

    async def redis_get(key):
        return await redis_client.get(key)

    async def redis_setex(key, ttl, value):
        return await redis_client.setex(key, ttl, value)

    proxy.get.side_effect = redis_get
    proxy.setex.side_effect = redis_setex
    keys = [old_key]
    try:
        await redis_client.setex(old_key, 60, json.dumps({"ig": ["'obsolete'"]}))
        assert await matched_ids(regional_session, "thread", "软件", redis=proxy) == {
            1,
            2,
            5,
            6,
            7,
            8,
        }
        new_key = proxy.setex.call_args.args[0]
        keys.append(new_key)
        assert new_key != old_key
        with patch(
            "shared.fts_utils.batch_cut", side_effect=AssertionError("应命中缓存")
        ):
            assert await matched_ids(
                regional_session, "booklist", "軟體", redis=proxy
            ) == {1, 2, 5, 6, 7, 8}
        assert proxy.setex.await_count == 1
    finally:
        await redis_client.delete(*keys)


@pytest.mark.asyncio
async def test_cache_versions_and_empty_markers_are_distinct(
    regional_session, monkeypatch
):
    """规则升级和默认/禁用豁免分别生成独立缓存键。"""
    proxy = AsyncMock()
    proxy.get.return_value = None
    keys = []
    for markers in (None, []):
        await matched_ids(
            regional_session, "thread", exclude="軟體", markers=markers, redis=proxy
        )
        keys.append(proxy.setex.call_args.args[0])
    monkeypatch.setattr(
        "shared.fts_utils.SEARCH_NORMALIZATION_VERSION",
        SEARCH_NORMALIZATION_VERSION + "-next",
    )
    await matched_ids(regional_session, "thread", exclude="軟體", redis=proxy)
    keys.append(proxy.setex.call_args.args[0])
    assert len(set(keys)) == 3


@pytest.mark.asyncio
async def test_booklist_repository_edit_reindexes(regional_session):
    """API 使用的仓储编辑入口必须更新向量，而非仅 ORM 直接编辑。"""
    repo = BooklistRepository(regional_session)
    row = await repo.update_booklist(1, title="遊戲合集", description="寬頻")
    assert row.title == "遊戲合集"
    assert row.description == "寬頻"
    assert 1 in await matched_ids(regional_session, "booklist", "宽带")
    assert 1 not in await matched_ids(regional_session, "booklist", "软件")
    await repo.update_booklist(1, description="軟體")
    assert 1 in await matched_ids(regional_session, "booklist", "软体")
    await repo.update_booklist(1, title="寬頻", description="")
    assert 1 not in await matched_ids(regional_session, "booklist", "软件")
    assert await repo.update_booklist(999, title="missing") is None


@pytest.mark.asyncio
async def test_booklist_exclude_only(regional_session):
    """书单列表只传反选词时也应使用共享规范化规则。"""
    rows, total = await BooklistRepository(regional_session).list_booklists(
        exclude_keywords="软体", limit=50
    )
    assert {row.id for row in rows} == {3, 4, 5, 6}
    assert total == 4
