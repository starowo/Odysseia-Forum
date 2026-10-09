from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from api.v1.dependencies.security import get_current_user
from api.v1.routers import meta
from core.tag_access_service import TagAccessService
from shared.tag_error import TagError


@pytest_asyncio.fixture
async def role_client(monkeypatch):
    """隔离配置和成员查询，验证真实 HTTP 路由而不访问 Discord。"""
    app = FastAPI()
    app.include_router(meta.router, prefix="/v1")
    # 登录信息中的身份组不作为本接口的实时核验依据。
    app.dependency_overrides[get_current_user] = lambda: {"id": "123", "roles": ["77"]}
    config = {
        "main_guild_id": 10,
        "management_role_id": "77",
        "bot_admin_user_ids": [],
    }
    monkeypatch.setattr(meta, "role_config", config)
    roles = AsyncMock(return_value=set())
    monkeypatch.setattr(TagAccessService, "roles", roles)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        yield client, config, roles, app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "management,bot_admin", [(False, False), (True, False), (False, True), (True, True)]
)
async def test_role_flags_are_independent(role_client, management, bot_admin):
    """两种身份独立判断，包括仅 BOT 管理员但没有管理组身份。"""
    client, config, roles, _ = role_client
    config["bot_admin_user_ids"] = ["123"] if bot_admin else []
    roles.return_value = {"77"} if management else set()
    response = await client.get("/v1/meta/role")
    assert response.status_code == 200
    assert response.json() == {
        "is_management_member": management,
        "is_bot_admin": bot_admin,
    }
    assert response.headers["Cache-Control"] == "private, no-store"
    roles.assert_awaited_once_with(123, 10)


@pytest.mark.asyncio
@pytest.mark.parametrize("bot_admin", [False, True])
async def test_missing_member_preserves_bot_admin(role_client, bot_admin):
    """成员不存在只影响管理组身份，不影响 BOT 管理员配置。"""
    client, config, roles, _ = role_client
    config["bot_admin_user_ids"] = [123] if bot_admin else []
    roles.side_effect = TagError("forbidden", "用户不是服务器成员", 403)
    response = await client.get("/v1/meta/role")
    assert response.status_code == 200
    assert response.json() == {"is_management_member": False, "is_bot_admin": bot_admin}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        TagError("permission_unavailable", "成员权限服务暂时不可用", 503),
        httpx.ConnectError("连接失败"),
        ValueError("成员响应格式错误"),
    ],
)
async def test_lookup_failure_is_not_false_role(role_client, error):
    """临时失败返回 503，不伪造两个 false 的身份响应。"""
    client, _, roles, _ = role_client
    roles.side_effect = error
    response = await client.get("/v1/meta/role")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "permission_unavailable"
    assert response.headers["Cache-Control"] == "private, no-store"


@pytest.mark.asyncio
async def test_role_requires_login(role_client):
    """未登录返回 401，不能查询管理身份。"""
    client, _, roles, app = role_client
    app.dependency_overrides[get_current_user] = lambda: None
    response = await client.get("/v1/meta/role")
    assert response.status_code == 401
    roles.assert_not_awaited()


@pytest.mark.asyncio
async def test_uninitialized_role_service(role_client, monkeypatch):
    """依赖尚未注入时明确返回 503。"""
    client, _, roles, _ = role_client
    monkeypatch.setattr(meta, "role_config", None)
    assert (await client.get("/v1/meta/role")).status_code == 503
    roles.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_management_configuration(role_client):
    """未配置管理组时无需成员查询，BOT 身份仍照常返回。"""
    client, config, roles, _ = role_client
    config.pop("management_role_id")
    config["bot_admin_user_ids"] = [123]
    response = await client.get("/v1/meta/role")
    assert response.json() == {"is_management_member": False, "is_bot_admin": True}
    roles.assert_not_awaited()


@pytest.mark.asyncio
async def test_role_is_refreshed_between_requests(role_client):
    """重复请求重新查询成员，角色撤销后不沿用旧结果。"""
    client, _, roles, _ = role_client
    roles.side_effect = [{"77"}, set()]
    assert (await client.get("/v1/meta/role")).json()["is_management_member"] is True
    assert (await client.get("/v1/meta/role")).json()["is_management_member"] is False
    assert roles.await_count == 2
