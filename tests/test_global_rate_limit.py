"""测试全局分钟限流、每日 Watch 与请求级去重状态。"""

import logging
import time
from datetime import datetime, time as datetime_time
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request, Response

import api.middleware.rate_limit_middleware as middleware_module
import api.v1.dependencies.rate_limit as dependency_module
import api.v1.dependencies.security as security_module
from api.middleware.rate_limit_middleware import RateLimitMiddleware
from api.v1.dependencies.security import VERIFIED_JWT_PAYLOAD_STATE_KEY
from dto.rate_limit import (
    GlobalRateLimitConfig,
    GlobalRateLimitResult,
    RateLimitConfig,
    RateLimitResult,
)
from shared.rate_limit import (
    get_watch_body,
    get_watch_reasons,
    get_watch_trigger_details,
)
from shared.rate_limit.rate_limit_engine import (
    _get_local_day_window,
    check_global_rate_limit,
)


class TestGlobalRateLimitEngine:
    """验证全局 Redis 原子检查的输入输出。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("minute_count", "daily_count", "watched", "daily_active", "allowed"),
        [
            (300, 1500, 0, 0, True),
            (301, 1500, 1, 0, False),
            (1, 1501, 1, 1, True),
            (2, 1502, 1, 1, True),
        ],
    )
    async def test_threshold_boundaries(
        self,
        minute_count,
        daily_count,
        watched,
        daily_active,
        allowed,
    ):
        """分钟和每日边界按严格大于阈值生效。"""
        redis = AsyncMock()
        redis.eval.return_value = [
            minute_count,
            42,
            daily_count,
            watched,
            daily_active,
        ]

        result = await check_global_rate_limit(
            redis,
            "123",
            GlobalRateLimitConfig(),
            now_timestamp=time.time(),
        )

        assert result.allowed is allowed
        assert result.minute_count == minute_count
        assert result.daily_count == daily_count
        assert result.watched is bool(watched)
        assert result.daily_watch_active is bool(daily_active)
        assert result.minute_remaining == max(0, 300 - minute_count)

    @pytest.mark.asyncio
    async def test_single_redis_call_contains_all_keys_and_settings(self):
        """每次全局检查仅调用一次 Redis，并传入三个状态 Key。"""
        redis = AsyncMock()
        redis.eval.return_value = [1, 60, 1, 0, 0]
        config = GlobalRateLimitConfig()

        await check_global_rate_limit(
            redis,
            "456",
            config,
            now_timestamp=time.time(),
        )

        redis.eval.assert_awaited_once()
        args = redis.eval.await_args.args
        assert args[1] == 3
        assert args[2] == "rate_limit:global:456"
        assert args[3].startswith("rate_limit:global:daily:")
        assert args[3].endswith(":456")
        assert args[4] == "rate_limit:watch:456"
        assert args[5] == 60
        assert 1 <= args[6] <= 25 * 60 * 60
        assert args[7:] == (300, 1500, 900)

    @pytest.mark.asyncio
    async def test_redis_failure_fails_open(self):
        """Redis 异常时返回可放行结果。"""
        redis = AsyncMock()
        redis.eval.side_effect = ConnectionError("redis unavailable")

        result = await check_global_rate_limit(
            redis,
            "123",
            GlobalRateLimitConfig(),
        )

        assert result.allowed is True
        assert result.watched is False
        assert result.minute_remaining == 300

    def test_local_day_expires_at_next_server_midnight(self):
        """每日计数使用服务器本地日期并在次日零点过期。"""
        local_now = datetime.combine(datetime.now().date(), datetime_time(23, 59))
        timestamp = time.mktime(local_now.timetuple())

        date_key, ttl = _get_local_day_window(timestamp)

        assert date_key == local_now.strftime("%Y%m%d")
        assert ttl == 60


class TestRateLimitRequestCoordination:
    """验证接口限流只登记原因，由中间件统一打印。"""

    @pytest.mark.asyncio
    async def test_search_limit_records_reason_and_1024_char_body(
        self, monkeypatch, caplog
    ):
        """搜索超限登记原因和截断请求体，但不自行打印日志。"""
        body = ("界" * 1100).encode()
        consumed = False

        async def receive():
            nonlocal consumed
            if consumed:
                return {"type": "http.disconnect"}
            consumed = True
            return {"type": "http.request", "body": body, "more_body": False}

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/search",
            "headers": [],
            "state": {},
        }
        request = Request(scope, receive)
        redis = AsyncMock()
        monkeypatch.setattr(dependency_module, "_search_config", RateLimitConfig(60))
        monkeypatch.setattr(dependency_module.RedisManager, "get_client", lambda: redis)
        monkeypatch.setattr(
            dependency_module,
            "check_rate_limit",
            AsyncMock(
                return_value=RateLimitResult(
                    allowed=False,
                    current_count=61,
                    remaining=0,
                    reset_after=30,
                )
            ),
        )
        set_watch = AsyncMock()
        monkeypatch.setattr(dependency_module, "set_rate_limit_watch", set_watch)

        with caplog.at_level(logging.WARNING), pytest.raises(HTTPException):
            await dependency_module.search_rate_limit(
                request,
                Response(),
                {"id": "123"},
            )

        assert get_watch_reasons(scope) == ["search_rate_limit"]
        assert get_watch_body(scope) == "界" * 1024
        detail = get_watch_trigger_details(scope)["search_rate_limit"]
        assert detail.current_count == 61
        assert detail.max_requests == 60
        assert detail.reset_after == 30
        set_watch.assert_awaited_once_with(redis, "123")
        assert not caplog.records


class TestRateLimitMiddlewareCoordination:
    """验证全局中间件的单请求单日志行为。"""

    @pytest.mark.asyncio
    async def test_daily_and_search_reasons_emit_one_log(self, monkeypatch, caplog):
        """每日 Watch 与搜索限流同时命中时只打印一次。"""
        body = b"x" * 1100

        async def app(scope, receive, send):
            message = await receive()
            dependency_module.add_watch_reason(
                scope,
                "search_rate_limit",
                message["body"].decode(),
                current_count=61,
                max_requests=60,
                reset_after=28,
            )
            await send({"type": "http.response.start", "status": 429, "headers": []})
            await send({"type": "http.response.body", "body": b"limited"})

        middleware = RateLimitMiddleware(
            app,
            jwt_secret="secret",
        )
        monkeypatch.setattr(
            middleware,
            "_extract_user_payload",
            AsyncMock(return_value={"id": "123"}),
        )
        monkeypatch.setattr(
            middleware_module.RedisManager, "get_client", lambda: AsyncMock()
        )
        monkeypatch.setattr(
            middleware_module,
            "check_global_rate_limit",
            AsyncMock(
                return_value=GlobalRateLimitResult(
                    allowed=True,
                    minute_count=61,
                    minute_remaining=239,
                    reset_after=30,
                    daily_count=1501,
                    watched=True,
                    daily_watch_active=True,
                )
            ),
        )
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/search",
            "headers": [(b"user-agent", b"pytest")],
            "state": {},
        }
        received = False

        async def receive():
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        sent = []

        async def send(message):
            sent.append(message)

        with caplog.at_level(logging.INFO):
            await middleware(scope, receive, send)

        watch_logs = [
            record.getMessage()
            for record in caplog.records
            if "WATCH:" in record.getMessage()
        ]
        assert len(watch_logs) == 1
        assert "reason=daily_watch,search_rate_limit" in watch_logs[0]
        assert "reason_cn=每日调用量监控,搜索接口限流" in watch_logs[0]
        assert "search_count=61/60 search_reset=28s" in watch_logs[0]
        assert f"body={'x' * 1024} " in watch_logs[0]
        assert sent[0]["status"] == 429

    @pytest.mark.asyncio
    async def test_global_301st_request_returns_429_and_one_log(
        self, monkeypatch, caplog
    ):
        """全局分钟硬限流不进入下游且只打印一次。"""
        app = AsyncMock()
        middleware = RateLimitMiddleware(app, jwt_secret="secret")
        monkeypatch.setattr(
            middleware,
            "_extract_user_payload",
            AsyncMock(return_value={"id": "123"}),
        )
        monkeypatch.setattr(
            middleware_module.RedisManager, "get_client", lambda: AsyncMock()
        )
        monkeypatch.setattr(
            middleware_module,
            "check_global_rate_limit",
            AsyncMock(
                return_value=GlobalRateLimitResult(
                    allowed=False,
                    minute_count=301,
                    minute_remaining=0,
                    reset_after=20,
                    daily_count=100,
                    watched=True,
                    daily_watch_active=False,
                )
            ),
        )
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/v1/tags",
            "headers": [],
            "state": {},
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent = []

        async def send(message):
            sent.append(message)

        with caplog.at_level(logging.WARNING):
            await middleware(scope, receive, send)

        assert app.await_count == 0
        assert sent[0]["status"] == 429
        assert (b"retry-after", b"20") in sent[0]["headers"]
        watch_logs = [
            record for record in caplog.records if "WATCH:" in record.getMessage()
        ]
        assert len(watch_logs) == 1
        assert "reason=global_rate_limit" in watch_logs[0].getMessage()
        assert "reason_cn=全局分钟限流" in watch_logs[0].getMessage()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path", ["/v1/auth/check", "/v1/health", "/v1/debug/memory"]
    )
    async def test_skip_paths_do_not_count(self, path, monkeypatch):
        """白名单路径不验证用户也不执行 Redis 全局计数。"""

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = RateLimitMiddleware(app, jwt_secret="secret")
        extract_user = AsyncMock(return_value={"id": "123"})
        check_global = AsyncMock()
        monkeypatch.setattr(middleware, "_extract_user_payload", extract_user)
        monkeypatch.setattr(middleware_module, "check_global_rate_limit", check_global)
        scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "state": {},
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            return None

        await middleware(scope, receive, send)

        extract_user.assert_not_awaited()
        check_global.assert_not_awaited()

    def test_authors_path_is_not_mistaken_for_auth_whitelist(self):
        """作者业务接口不会因共享字符串前缀被错误跳过。"""
        assert RateLimitMiddleware._should_skip_path("/v1/authors") is False
        assert RateLimitMiddleware._should_skip_path("/v1/authors/123") is False

    def test_only_v1_paths_are_counted(self):
        """根路径和相似字符串路径不属于 v1 业务接口。"""
        assert RateLimitMiddleware._is_v1_path("/") is False
        assert RateLimitMiddleware._is_v1_path("/v10/tags") is False
        assert RateLimitMiddleware._is_v1_path("/v1/tags") is True

    @pytest.mark.asyncio
    async def test_unauthenticated_request_does_not_count(self, monkeypatch):
        """没有有效 JWT 的请求不执行 Redis 全局计数。"""
        app = AsyncMock()
        middleware = RateLimitMiddleware(app, jwt_secret="secret")
        check_global = AsyncMock()
        monkeypatch.setattr(
            middleware, "_extract_user_payload", AsyncMock(return_value=None)
        )
        monkeypatch.setattr(middleware_module, "check_global_rate_limit", check_global)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/v1/tags",
            "headers": [],
            "state": {},
        }

        await middleware(scope, AsyncMock(), AsyncMock())

        app.assert_awaited_once()
        check_global.assert_not_awaited()
        assert scope["state"][VERIFIED_JWT_PAYLOAD_STATE_KEY] is None


class TestVerifiedJwtReuse:
    """验证认证依赖复用中间件已验证的 JWT。"""

    @pytest.mark.asyncio
    async def test_get_current_user_reuses_cached_payload(self, monkeypatch):
        """请求状态已有验证结果时不重复执行 JWT 验签。"""
        payload = {"id": "123", "roles": []}
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/v1/tags",
            "headers": [],
            "state": {VERIFIED_JWT_PAYLOAD_STATE_KEY: payload},
        }
        request = Request(scope)
        verify_jwt = AsyncMock()
        monkeypatch.setattr(security_module, "_JWT_SECRET", "secret")
        monkeypatch.setattr(security_module, "verify_jwt", verify_jwt)

        result = await security_module.get_current_user(request, None)

        assert result == payload
        verify_jwt.assert_not_awaited()
