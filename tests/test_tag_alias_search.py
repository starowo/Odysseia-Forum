# ruff: noqa: F811
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from test_custom_tag_governance import setup_tags  # noqa: F401
from core.booklist_repository import BooklistRepository
from core.tag_query import tag_name_filters
from core.tag_cache_service import TagCacheService
from models import Tag, TagAlias, TagBinding, Thread, Booklist
from search.search_service import SearchService
from search.qo.thread_search import ThreadSearchQuery
from shared.time_utils import utc_now


@pytest.mark.asyncio
async def test_alias_groups_and_real_search_pagination(setup_tags):
    """真实绑定覆盖名称并集、别名大小写、AND/OR、状态及双目标分页。"""
    factory, _, _ = setup_tags
    async with factory() as session, session.begin():
        session.add_all(
            [
                Tag(id=1, name="测试", source="custom", category=3),
                Tag(
                    id=2,
                    name="试测",
                    source="discord",
                ),
                Tag(id=3, name="其他", source="custom", category=2, enabled=False),
                Tag(
                    id=4, name="删除", source="custom", category=3, deleted_at=utc_now()
                ),
                Tag(id=5, name="转换", source="custom", originated_from_discord=True),
            ]
        )
        session.add_all(
            [
                TagAlias(tag_id=i, name=name)
                for i, name in [
                    (1, "试测"),
                    (1, "Alice"),
                    (3, "试测"),
                    (4, "已删除"),
                    (5, "Converted"),
                ]
            ]
        )
        for i in (1, 2, 3, 4, 5):
            session.add(
                Thread(
                    id=i,
                    thread_id=1000 + i,
                    channel_id=20 if i < 3 else 30,
                    guild_id=10,
                    author_id=1,
                    title="正文",
                    show_flag=True,
                )
            )
            if i != 1:
                session.add(Booklist(id=i, owner_id=1, title="书单", is_public=True))
            for kind in ("thread", "booklist"):
                session.add(
                    TagBinding(
                        target_type=kind, target_id=i, tag_id=i, binding_source="local"
                    )
                )
        session.add(
            TagBinding(
                target_type="thread",
                target_id=5,
                tag_id=1,
                ended_at=utc_now(),
                binding_source="local",
            )
        )
        await session.flush()
        cases = [
            (["试测"], [], "and", {1, 2, 3}),
            (["ALICE"], [], "and", {1}),
            (["Ali"], [], "and", set()),
            (["不存在"], [], "and", set()),
            (["试测", "ALICE"], [], "and", {1}),
            (["试测", "不存在"], [], "and", set()),
            (["ALICE", "不存在"], [], "or", {1}),
            (["ALICE", "Converted"], [], "or", {1, 5}),
            (["试测", "试测"], ["alice"], "and", {2, 3}),
            (["试测"], ["未知"], "and", {1, 2, 3}),
            (["已删除"], [], "and", set()),
            (["Converted"], [], "and", {5}),
            (["测试"], [], "and", {1}),
        ]
        for kind, model in (("thread", Thread), ("booklist", Booklist)):
            for included, excluded, logic, expected in cases:
                filters = await tag_name_filters(
                    session, kind, model.id, included, excluded, logic
                )
                actual = set(
                    (await session.execute(select(model.id).where(*filters))).scalars()
                )
                assert actual == expected, (kind, included, excluded, logic, actual)
        books, total = await BooklistRepository(session).list_booklists(
            include_tags=["试测"], limit=1, offset=1
        )
        assert len(books) == 1 and total == 3
        books, total = await BooklistRepository(session).list_booklists(
            include_tags=["试测"], include_tag_ids=[1], exclude_tags=["ALICE"]
        )
        assert books == [] and total == 0
        service = SearchService(session, TagCacheService(factory))
        threads, total = await service.search_threads_with_count(
            ThreadSearchQuery(include_tags=["试测"], channel_ids=[20]),
            limit=1,
            offset=1,
            total_display_count=100,
            exploration_factor=0,
            strength_weight=1,
        )
        assert len(threads) == 1 and total == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", ["/v1/booklist/list/page", "/v1/booklist/my/list/page"]
)
async def test_booklist_alias_query_http(path, monkeypatch):
    """通过 HTTP 确认重复名称参数传递到书单查询。"""
    import httpx
    from fastapi import FastAPI
    from api.v1.routers import booklists
    from api.v1.dependencies.security import get_current_user, require_auth

    app = FastAPI()
    app.include_router(booklists.router, prefix="/v1")
    app.dependency_overrides[get_current_user] = lambda: {"id": "1"}
    app.dependency_overrides[require_auth] = lambda: {"id": "1"}
    session = AsyncMock()
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(booklists, "AsyncSessionFactory", factory)
    query = AsyncMock(return_value=([], 0))
    monkeypatch.setattr(BooklistRepository, "list_booklists", query)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            path,
            params=[
                ("include_tags", "试测"),
                ("include_tags", "ALICE"),
                ("exclude_tags", "排除"),
            ],
        )
    assert response.status_code == 200, response.text
    assert query.call_args.kwargs["include_tags"] == ["试测", "ALICE"]
    assert query.call_args.kwargs["exclude_tags"] == ["排除"]
