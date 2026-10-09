from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from api.main import app
from api.v1.dependencies.security import require_auth
from api.v1.routers import tags
from api.v1.schemas.booklist.booklist_summary import BooklistSummary
from api.v1.schemas.search.search_request import SearchRequest
from api.v1.schemas.search.thread_detail import ThreadDetail
from api.v1.schemas.tags.tag_proposal_request import TagProposalRequest
from api.v1.schemas.tags.tag_selection_request import TagSelectionRequest
from api.v1.schemas.tags.tag_update_request import TagUpdateRequest
from core.tag_query import load_custom_tags
from dto.custom_tag_binding_response import CustomTagBindingResponse

BIG_ID = 9007199254740993


def test_openapi_request_ids_and_structured_responses():
    """核对实际应用的路径、请求体、查询参数和响应类型契约。"""
    schema = app.openapi()
    models = schema["components"]["schemas"]
    checked_paths = 0
    checked_queries = 0
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            for parameter in operation.get("parameters", []):
                if path.startswith("/v1/tags") and parameter["name"].endswith("_id"):
                    branches = parameter["schema"]["anyOf"]
                    assert {item["type"] for item in branches} == {"string", "integer"}
                    checked_paths += 1
                if parameter["name"] in {"include_tag_ids", "exclude_tag_ids"}:
                    array = parameter["schema"]
                    if "anyOf" in array:
                        array = next(
                            item for item in array["anyOf"] if item["type"] == "array"
                        )
                    assert {item["type"] for item in array["items"]["anyOf"]} == {
                        "string",
                        "integer",
                    }
                    checked_queries += 1
    assert checked_paths > 10
    assert checked_queries == 4
    for name, fields in {
        "TagProposalRequest": ["tag_id"],
        "TagRelationRequest": ["target_tag_id"],
        "TagSelectionRequest": ["tag_ids"],
        "SearchRequest": ["include_tag_ids", "exclude_tag_ids"],
    }.items():
        for field in fields:
            prop = models[name]["properties"][field]
            prop = prop.get("items", prop)
            assert {item["type"] for item in prop["anyOf"]} == {"string", "integer"}
    for model in (ThreadDetail, BooklistSummary):
        prop = model.model_json_schema(mode="serialization")["properties"][
            "custom_tags"
        ]
        assert prop["items"]["$ref"].endswith("/CustomTagBindingResponse")
    binding = models["CustomTagBindingResponse"]
    assert binding["properties"]["id"]["type"] == "string"
    assert binding["properties"]["binding_id"]["type"] == "string"
    assert set(binding["required"]) == set(binding["properties"]) - {
        "binding_source",
        "readonly",
    }
    assert binding["properties"]["binding_source"]["const"] == "local"
    assert binding["properties"]["readonly"]["const"] is False


@pytest.mark.parametrize("value", [BIG_ID, str(BIG_ID)])
def test_large_ids_are_normalized_without_precision_loss(value):
    """大 ID 的两种输入形式均转换为准确的 Python 整数。"""
    assert TagProposalRequest(tag_id=value).tag_id == BIG_ID
    selection = TagSelectionRequest(version="v", tag_ids=[value, "123"])
    assert selection.tag_ids == [BIG_ID, 123]
    search = SearchRequest(include_tag_ids=[value, "123"], exclude_tag_ids=[value])
    assert search.include_tag_ids == [BIG_ID, 123]
    assert search.exclude_tag_ids == [BIG_ID]


@pytest.mark.parametrize(
    "value", ["abc", "1.2", "1e3", "", None, True, 1.5, 0, -1, "0", "-1"]
)
def test_proposal_rejects_invalid_ids(value):
    """非法输入和非正数 ID 不进入业务层。"""
    with pytest.raises(ValidationError):
        TagProposalRequest(tag_id=value)


@pytest.mark.asyncio
async def test_http_path_and_body_ids_are_normalized(monkeypatch):
    """真实 HTTP 请求在进入事件分发前已完成大 ID 校验。"""
    application = FastAPI()
    application.include_router(tags.router, prefix="/v1")
    application.dependency_overrides[require_auth] = lambda: {"id": "123"}
    dispatch = AsyncMock(
        return_value={
            "id": str(BIG_ID),
            "tag_id": str(BIG_ID),
            "tag_name": "测试",
            "is_abyss": False,
            "status": "pending",
            "reason": None,
            "created_at": "2026-09-14T00:00:00Z",
            "due_at": "2026-09-21T00:00:00Z",
            "resolved_at": None,
        }
    )
    monkeypatch.setattr(tags, "dispatch", dispatch)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(application), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/v1/tags/thread/{BIG_ID}/proposals", json={"tag_id": str(BIG_ID)}
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(BIG_ID)
        assert dispatch.call_args.kwargs["target_id"] == BIG_ID
        assert dispatch.call_args.kwargs["tag_id"] == BIG_ID
        dispatch.return_value = {
            "id": str(BIG_ID),
            "name": "测试",
            "is_abyss": False,
            "source": "custom",
            "discord_sources": [],
            "category": 3,
            "category_name": "角色",
            "enabled": False,
            "deleted_at": None,
        }
        response = await client.patch(f"/v1/tags/{BIG_ID}", json={"enabled": False})
        assert response.status_code == 200
        assert dispatch.call_args.kwargs["tag_id"] == BIG_ID
        dispatch.reset_mock()
        for url in ["/v1/tags/thread/abc", "/v1/tags/thread/1.2"]:
            assert (await client.get(url)).status_code == 422
        for value in ["abc", "0", "-1"]:
            assert (
                await client.patch(f"/v1/tags/{value}", json={"enabled": False})
            ).status_code == 422
        dispatch.assert_not_awaited()


def test_update_schema_matches_validation():
    """省略字段不修改，显式空值被拒绝，false 和合法单字段更新可用。"""
    schema = TagUpdateRequest.model_json_schema()
    assert not schema.get("required")
    for prop in schema["properties"].values():
        assert "anyOf" not in prop
        assert "default" not in prop
        assert prop["type"] != "null"
    assert schema["properties"]["category"]["minimum"] == 1
    assert schema["properties"]["category"]["maximum"] == 7
    for payload in [
        {},
        {"name": None},
        {"category": None},
        {"enabled": None},
        {"is_abyss": None},
        {"name": ""},
        {"category": 8},
    ]:
        with pytest.raises(ValidationError):
            TagUpdateRequest.model_validate(payload)
    for payload in [
        {"name": "爱丽丝"},
        {"category": 3},
        {"enabled": False},
        {"is_abyss": True},
    ]:
        assert (
            TagUpdateRequest.model_validate(payload).model_dump(exclude_unset=True)
            == payload
        )


@pytest.mark.asyncio
async def test_custom_tags_are_assembled_as_typed_models():
    """批量装配生成共享 DTO，响应序列化保留完整字符串 ID。"""
    binding = SimpleNamespace(id=BIG_ID + 1, target_id=BIG_ID, upvotes=3, downvotes=1)
    tag = SimpleNamespace(
        id=BIG_ID,
        name="爱丽丝(BA)",
        is_abyss=True,
        category=3,
        enabled=False,
        source="custom",
    )
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [(binding, tag)]))
    )
    result = await load_custom_tags(session, "thread", [BIG_ID])
    item = result[BIG_ID][0]
    assert isinstance(item, CustomTagBindingResponse)
    data = item.model_dump(mode="json")
    assert data == {
        "id": str(BIG_ID),
        "name": "爱丽丝(BA)",
        "is_abyss": True,
        "category": 3,
        "category_name": "角色",
        "source": "custom",
        "enabled": False,
        "binding_id": str(BIG_ID + 1),
        "upvotes": 3,
        "downvotes": 1,
        "binding_source": "local",
        "readonly": False,
    }
    # 装配入口可能先构造响应后赋值，验证该路径不会遗留原始字典。
    for model in (ThreadDetail, BooklistSummary):
        response = model.model_construct(custom_tags=[])
        response.custom_tags = result[BIG_ID]
        assert response.model_dump(mode="json")["custom_tags"] == [data]
