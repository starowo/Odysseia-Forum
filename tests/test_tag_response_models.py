from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from api.main import app
from api.v1.dependencies.security import require_auth
from api.v1.routers import tags
from shared.tag_error import TagError

BIG_ID = "9007199254740993"
TAG = {
    "id": BIG_ID,
    "name": "测试",
    "description": "",
    "is_abyss": False,
    "source": "custom",
    "discord_sources": [],
    "category": 3,
    "category_name": "角色",
    "enabled": True,
    "deleted_at": None,
}


@pytest_asyncio.fixture
async def response_client(monkeypatch):
    """隔离事件处理，保留真实路由的响应校验与错误转换。"""
    application = FastAPI()
    application.include_router(tags.router, prefix="/v1")
    application.dependency_overrides[require_auth] = lambda: {"id": "1"}
    mediator = AsyncMock()
    monkeypatch.setattr(tags, "event_mediator", mediator)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(application), base_url="http://test"
    ) as client:
        yield client, mediator


def test_all_tag_routes_have_response_schema():
    """实际 OpenAPI 的每个标签成功响应都引用具体模型。"""
    schema = app.openapi()
    for path, operations in schema["paths"].items():
        if not path.startswith("/v1/tags"):
            continue
        for operation in operations.values():
            for code, response in operation["responses"].items():
                if code.startswith("2"):
                    body = response["content"]["application/json"]["schema"]
                    assert "$ref" in body or "$ref" in body.get("items", {})
    items = schema["components"]["schemas"]["TargetTagsResponse"]["properties"]["tags"][
        "items"
    ]
    assert items["discriminator"]["propertyName"] == "binding_source"
    assert set(items["discriminator"]["mapping"]) == {"discord_sync", "local"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body,code",
    [
        ("POST", "", {"name": "测试", "category": 3}, 201),
        ("PATCH", "/123", {"enabled": False}, 200),
        ("DELETE", "/123", None, 200),
        ("POST", "/123/restore", None, 200),
        ("PUT", "/123/aliases", {"aliases": []}, 200),
        ("POST", "/123/relations", {"target_tag_id": "456", "kind": "implies"}, 200),
        ("DELETE", "/123/relations/implies/456", None, 200),
    ],
)
async def test_management_response_fields(response_client, method, path, body, code):
    """所有管理操作保留原有标签实体字段和状态码。"""
    client, mediator = response_client
    mediator.request.return_value = TAG
    response = await client.request(method, "/v1/tags" + path, json=body)
    assert response.status_code == code
    assert response.json() == TAG


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/thread/123", None),
        ("PUT", "/booklist/123", {"version": "v", "tag_ids": []}),
        ("PUT", "/thread/123/votes/456", {"vote": -1}),
    ],
)
async def test_snapshot_preserves_native_and_custom_fields(
    response_client, method, path, body
):
    """联合模型保留本人票数，原生标签不增加绑定或投票字段。"""
    client, mediator = response_client
    native = dict(
        TAG,
        source="discord",
        discord_source_id=BIG_ID,
        category=None,
        category_name=None,
        readonly=True,
        binding_source="discord_sync",
    )
    custom = dict(
        TAG,
        readonly=False,
        binding_source="local",
        binding_id=BIG_ID,
        upvotes=3,
        downvotes=1,
        my_vote=-1,
    )
    expected = {
        "version": "v",
        "tags": [native, custom],
        "over_limit": False,
        "conflicting_pairs": [],
    }
    mediator.request.return_value = expected
    response = await client.request(method, "/v1/tags" + path, json=body)
    assert response.status_code == 200
    assert response.json() == expected
    assert "actor_id" not in response.json()["tags"][1]
    mediator.request.return_value = {"version": "v", "tags": []}
    assert (await client.get("/v1/tags/thread/123")).json() == {
        "version": "v",
        "tags": [],
        "over_limit": False,
        "conflicting_pairs": [],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["pending", "approved", "rejected", "failed"])
async def test_proposal_states_and_utc(response_client, state):
    """提议、审核及列表接口保留状态和可空字段，时间明确为 UTC。"""
    client, mediator = response_client
    value = {
        "id": BIG_ID,
        "tag_id": BIG_ID,
        "tag_name": "测试",
        "is_abyss": False,
        "status": state,
        "reason": None if state == "pending" else "review",
        "created_at": datetime(2026, 9, 14),
        "due_at": datetime(2026, 9, 21),
        "resolved_at": None if state == "pending" else datetime(2026, 9, 15),
    }
    mediator.request.return_value = value
    for method, path, body in [
        ("POST", "/thread/123/proposals", {"tag_id": BIG_ID}),
        ("PUT", "/thread/123/proposals/456", {"approve": True}),
    ]:
        response = await client.request(method, "/v1/tags" + path, json=body)
        assert response.status_code == 200
        result = response.json()
        assert set(result) == set(value)
        assert result["status"] == state
        assert result["id"] == BIG_ID
        assert result["created_at"] == "2026-09-14T00:00:00Z"
        assert result["resolved_at"] == (
            None if state == "pending" else "2026-09-15T00:00:00Z"
        )
    mediator.request.return_value = [value]
    for query in ["", "?review_queue=true"]:
        assert (await client.get("/v1/tags/thread/123/proposals" + query)).json() == [
            result
        ]


@pytest.mark.asyncio
async def test_lists_audit_details_and_permission_error(response_client):
    """标签池返回统计包装，其余列表与审计错误契约保持不变。"""
    client, mediator = response_client
    response = await client.get("/v1/tags/categories")
    assert len(response.json()) == 7
    pool_item = dict(TAG, aliases=["Alice"])
    mediator.request.return_value = [pool_item]
    assert (await client.get("/v1/tags")).json() == {
        "results": [pool_item],
        "total": 1,
    }
    for path, value in [
        ("/relations", {"source_id": BIG_ID, "target_id": "123", "kind": "implies"}),
        (
            "/tag/123/audit",
            {
                "id": BIG_ID,
                "type": "tag.pool.delete",
                "actor_id": None,
                "tag_id": BIG_ID,
                "detail": {"nested": {"items": [None, True, 1, "x"]}},
                "created_at": "2026-09-14T00:00:00Z",
            },
        ),
    ]:
        mediator.request.return_value = [value]
        assert (await client.get("/v1/tags" + path)).json() == [value]
    mediator.request.return_value = []
    assert (await client.get("/v1/tags")).json() == {"results": [], "total": 0}
    for path in ["/relations", "/thread/123/proposals", "/thread/123/audit"]:
        mediator.request.return_value = []
        assert (await client.get("/v1/tags" + path)).json() == []
    mediator.request.side_effect = TagError("forbidden", "无审计权限", 403)
    for path in ["/thread/123/audit", "/booklist/123/audit", "/tag/123/audit"]:
        assert (await client.get("/v1/tags" + path)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("source", [None, "custom", "discord"])
async def test_pool_source_parameter(response_client, source):
    """来源筛选透传到领域事件，省略参数保持全部来源。"""
    client, mediator = response_client
    mediator.request.return_value = []
    response = await client.get(
        "/v1/tags", params={} if source is None else {"source": source}
    )
    assert response.status_code == 200
    assert response.json() == {"results": [], "total": 0}
    assert mediator.request.call_args.args[0].payload["source"] == source


def test_pool_openapi_has_non_paginated_response():
    """标签池契约使用 results 与 total，并移除 offset 查询参数。"""
    operation = app.openapi()["paths"]["/v1/tags"]["get"]
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "q",
        "source",
        "category",
        "selectable",
        "include_deleted",
    }
    schema = app.openapi()["components"]["schemas"]["TagPoolResponse"]
    assert schema["required"] == ["results", "total"]


@pytest.mark.asyncio
async def test_pool_rejects_invalid_source(response_client):
    """非法来源由接口校验拒绝，不进入业务层。"""
    client, mediator = response_client
    response = await client.get("/v1/tags", params={"source": "invalid"})
    assert response.status_code == 422
    mediator.request.assert_not_called()
