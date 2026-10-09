from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.v1.routers import open_graph
from dto.open_graph import (
    AuthorShareMetadataDTO,
    AuthorShareStatsDTO,
    BooklistShareMetadataDTO,
    BooklistShareStatsDTO,
    OpenGraphAuthorDTO,
    ThreadShareMetadataDTO,
    ThreadShareStatsDTO,
)


@pytest.mark.asyncio
async def test_missing_service_token_configuration_returns_503(monkeypatch):
    """服务端未配置令牌时接口不可用。"""
    monkeypatch.setattr(open_graph, "_service_token", None)
    with pytest.raises(HTTPException) as exc_info:
        await open_graph.require_open_graph_service_token("Bearer anything")
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_missing_or_wrong_service_token_returns_401(monkeypatch):
    """缺失、错误或错误认证方案均返回 401。"""
    monkeypatch.setattr(open_graph, "_service_token", "correct-secret")
    for authorization in (None, "Bearer wrong-secret", "Basic correct-secret"):
        with pytest.raises(HTTPException) as exc_info:
            await open_graph.require_open_graph_service_token(authorization)
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_three_resource_routes_return_service_dtos(monkeypatch):
    """帖子、作者和书单路由分别返回新响应契约。"""
    now = datetime(2026, 8, 8)
    thread_metadata = ThreadShareMetadataDTO(
        title="帖子",
        author=OpenGraphAuthorDTO(display_name="作者"),
        stats=ThreadShareStatsDTO(reaction_count=1, reply_count=2, collection_count=3),
        created_at=now,
        updated_at=now,
    )
    author_metadata = AuthorShareMetadataDTO(
        display_name="作者",
        stats=AuthorShareStatsDTO(thread_count=1, reaction_count=2, reply_count=3),
        works=[],
        updated_at=now,
    )
    booklist_metadata = BooklistShareMetadataDTO(
        title="书单",
        works=[],
        stats=BooklistShareStatsDTO(item_count=0, collection_count=1, view_count=2),
        is_tournament=False,
        created_at=now,
        updated_at=now,
    )
    thread_service = MagicMock()
    thread_service.get_share_metadata = AsyncMock(return_value=thread_metadata)
    author_service = MagicMock()
    author_service.get_share_metadata = AsyncMock(return_value=author_metadata)
    booklist_service = MagicMock()
    booklist_service.get_share_metadata = AsyncMock(return_value=booklist_metadata)
    monkeypatch.setattr(open_graph, "_thread_open_graph_service", thread_service)
    monkeypatch.setattr(open_graph, "_author_open_graph_service", author_service)
    monkeypatch.setattr(open_graph, "_booklist_open_graph_service", booklist_service)

    assert (await open_graph.get_thread_share_metadata(1)).title == "帖子"
    assert (await open_graph.get_author_share_metadata(2)).display_name == "作者"
    result = await open_graph.get_booklist_share_metadata(3)
    assert result.cover_image_url is None
    assert "image_url" not in result.model_dump()
    assert "item_count" not in result.model_dump()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service_name, endpoint",
    [
        ("_thread_open_graph_service", open_graph.get_thread_share_metadata),
        ("_author_open_graph_service", open_graph.get_author_share_metadata),
        ("_booklist_open_graph_service", open_graph.get_booklist_share_metadata),
    ],
)
async def test_hidden_or_missing_resources_share_404(
    monkeypatch, service_name, endpoint
):
    """三类服务隐藏的资源均由路由映射为 404。"""
    service = MagicMock()
    service.get_share_metadata = AsyncMock(return_value=None)
    monkeypatch.setattr(open_graph, service_name, service)
    with pytest.raises(HTTPException) as exc_info:
        await endpoint(99)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_service_failure_returns_sanitized_500(monkeypatch, caplog):
    """内部异常只返回与记录稳定消息，不泄露异常详情。"""
    service = MagicMock()
    service.get_share_metadata = AsyncMock(
        side_effect=RuntimeError("signed-url-and-secret")
    )
    monkeypatch.setattr(open_graph, "_thread_open_graph_service", service)

    with pytest.raises(HTTPException) as exc_info:
        await open_graph.get_thread_share_metadata(99)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "分享元数据生成失败"
    assert "signed-url-and-secret" not in caplog.text


def test_non_get_method_and_invalid_path_parameter_use_fastapi_defaults(monkeypatch):
    """非 GET 方法返回 405，无法解析的整数路径参数返回 422。"""
    monkeypatch.setattr(open_graph, "_service_token", "correct-secret")
    app = FastAPI()
    app.include_router(open_graph.router, prefix="/v1")
    client = TestClient(app)
    headers = {"Authorization": "Bearer correct-secret"}

    method_response = client.post(
        "/v1/internal/share-metadata/threads/1", headers=headers
    )
    validation_response = client.get(
        "/v1/internal/share-metadata/threads/not-an-int", headers=headers
    )

    assert method_response.status_code == 405
    assert validation_response.status_code == 422
