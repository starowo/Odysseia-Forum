"""全局限流 ASGI 中间件。

对所有 /v1/* 请求按 user_id 做 Redis 固定窗口计数，
白名单路径（/v1/health、/v1/auth、/v1/debug）跳过。
"""

import logging
from typing import Any, Dict, Optional

from api.v1.dependencies.security import VERIFIED_JWT_PAYLOAD_STATE_KEY
from api.v1.utils.jwt_utils import verify_jwt
from dto.rate_limit import GlobalRateLimitConfig, GlobalRateLimitResult
from shared.enum.rate_limit_defaults import RateLimitDefaults
from shared.enum.rate_limit_reason import RateLimitReason
from shared.rate_limit import (
    add_watch_reason,
    check_global_rate_limit,
    get_watch_body,
    get_watch_reasons,
    get_watch_trigger_details,
)
from shared.redis_client import RedisManager

logger = logging.getLogger(__name__)

# 不限流的路径前缀
_SKIP_PREFIXES = ("/v1/health", "/v1/auth", "/v1/debug")


class RateLimitMiddleware:
    """全局请求频率限制中间件。

    在 CORS 之后、路由之前执行。
    Redis 不可用时 fail-open，不影响正常请求。
    """

    def __init__(
        self,
        app,
        config: Optional[dict] = None,
        jwt_secret: Optional[str] = None,
    ):
        self.app = app
        self._config = GlobalRateLimitConfig.from_mapping(config)
        self._jwt_secret = jwt_secret

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        if not self._is_v1_path(path) or self._should_skip_path(path):
            await self.app(scope, receive, send)
            return

        payload = await self._extract_user_payload(scope)
        scope.setdefault("state", {})[VERIFIED_JWT_PAYLOAD_STATE_KEY] = payload
        user_id = payload.get("id") if payload else None
        if not user_id:
            await self.app(scope, receive, send)
            return

        try:
            redis = RedisManager.get_client()
            result = await check_global_rate_limit(
                redis=redis,
                user_id=str(user_id),
                config=self._config,
            )
        except Exception:
            logger.warning("Redis 全局频率限制未初始化，降级放行", exc_info=True)
            result = GlobalRateLimitResult.fail_open(self._config.max_requests)

        # 先登记全局触发原因，供所有限频规则统一输出
        if result.daily_watch_active:
            add_watch_reason(scope, RateLimitReason.DAILY_WATCH)
        if not result.allowed:
            add_watch_reason(scope, RateLimitReason.GLOBAL_RATE_LIMIT)

        body = None
        downstream_receive = receive
        if result.watched:
            body_bytes, replay_receive = await self._read_and_replay_body(receive)
            body = self._truncate_body(
                body_bytes, max_len=int(RateLimitDefaults.LOG_BODY_MAX_CHARS)
            )
            downstream_receive = replay_receive

        if not result.allowed:
            self._log_watch(scope, str(user_id), result, body)
            await self._send_429(send, result.reset_after)
            return

        try:
            await self._send_with_headers(scope, downstream_receive, send, result)
        finally:
            reasons = get_watch_reasons(scope)
            if result.watched or reasons:
                self._log_watch(scope, str(user_id), result, body)

    @staticmethod
    async def _read_and_replay_body(receive):
        """读取 ASGI body 并返回一个可重放的 receive。

        仅对 watched 用户调用，确保下游 FastAPI 仍能正常读取 body。
        """
        body_chunks = []
        more_body = True
        while more_body:
            message = await receive()
            body_chunks.append(message.get("body", b""))
            more_body = message.get("more_body", False)

        body_bytes = b"".join(body_chunks)
        replayed = False

        async def _replay_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {
                    "type": "http.request",
                    "body": body_bytes,
                    "more_body": False,
                }
            return await receive()

        return body_bytes, _replay_receive

    @staticmethod
    def _truncate_body(body_bytes: bytes, max_len: int = 1024) -> str:
        """截断 body 用于日志输出。"""
        if not body_bytes:
            return "-"
        return body_bytes.decode("utf-8", errors="replace")[:max_len]

    @staticmethod
    def _get_header(scope, name: str) -> str:
        """从 ASGI scope 中读取指定 header，找不到返回 '-'。"""
        for h_name, h_value in scope.get("headers", []):
            if h_name.decode("latin-1").lower() == name.lower():
                return h_value.decode("latin-1", errors="replace")[:256]
        return "-"

    @staticmethod
    def _should_skip_path(path: str) -> bool:
        """判断路径是否属于完整的白名单前缀。"""
        return any(
            path == prefix or path.startswith(f"{prefix}/") for prefix in _SKIP_PREFIXES
        )

    @staticmethod
    def _is_v1_path(path: str) -> bool:
        """判断路径是否属于 v1 API。"""
        return path == "/v1" or path.startswith("/v1/")

    async def _extract_user_payload(self, scope) -> Optional[Dict[str, Any]]:
        """从请求中解析并验证 JWT，失败时返回 None。"""
        if not self._jwt_secret:
            return None

        token = None

        # 优先解析 Authorization Bearer
        for name, value in scope.get("headers", []):
            name = name.decode("latin-1").lower()
            if name == "authorization" and value:
                val = value.decode("latin-1")
                if val.startswith("Bearer "):
                    token = val[7:]
                    break

        # 回退到 Cookie 会话
        if not token:
            for name, value in scope.get("headers", []):
                if name.decode("latin-1").lower() == "cookie":
                    cookie_str = value.decode("latin-1")
                    for item in cookie_str.split(";"):
                        item = item.strip()
                        if item.startswith("session="):
                            token = item[8:]
                            break
                    break

        if not token:
            return None

        return await verify_jwt(token, self._jwt_secret)

    def _log_watch(
        self,
        scope,
        user_id: str,
        result: GlobalRateLimitResult,
        body: str | None,
    ) -> None:
        """为当前请求输出至多一条 Watch 轨迹。"""
        reasons = get_watch_reasons(scope)
        effective_reasons = reasons or [RateLimitReason.ACTIVE_WATCH]
        reason_text = ",".join(effective_reasons)
        reason_cn = ",".join(
            RateLimitReason.chinese_label_for(reason) for reason in effective_reasons
        )
        tracked_body = get_watch_body(scope) or body or "-"
        trigger_metrics = self._format_trigger_metrics(scope)
        log_method = (
            logger.warning
            if any(reason.endswith("rate_limit") for reason in reasons)
            else logger.info
        )
        log_method(
            "WATCH: user_id=%s method=%s path=%s ua=%s body=%s reason=%s "
            "reason_cn=%s%s minute_count=%s/%s daily_count=%s",
            user_id,
            scope.get("method", "-"),
            scope.get("path", "-"),
            self._get_header(scope, "user-agent"),
            tracked_body[: int(RateLimitDefaults.LOG_BODY_MAX_CHARS)],
            reason_text,
            reason_cn,
            f" {trigger_metrics}" if trigger_metrics else "",
            result.minute_count,
            self._config.max_requests,
            result.daily_count,
        )

    @staticmethod
    def _format_trigger_metrics(scope) -> str:
        """格式化搜索和相似推荐限流的独立窗口计数。"""
        prefixes = {
            RateLimitReason.SEARCH_RATE_LIMIT: "search",
            RateLimitReason.SIMILAR_RATE_LIMIT: "similar",
        }
        metrics = []
        for reason, detail in get_watch_trigger_details(scope).items():
            prefix = prefixes.get(reason)
            if not prefix:
                continue
            metrics.extend(
                [
                    f"{prefix}_count={detail.current_count}/{detail.max_requests}",
                    f"{prefix}_reset={detail.reset_after}s",
                ]
            )
        return " ".join(metrics)

    async def _send_429(self, send, reset_after: int) -> None:
        body = '{"detail":"请求过于频繁，请稍后重试"}'.encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", str(reset_after).encode()),
                    (b"x-ratelimit-remaining", b"0"),
                    (b"x-ratelimit-reset", str(reset_after).encode()),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )

    async def _send_with_headers(self, scope, receive, send, result) -> None:
        """包装 send 以注入限流响应头。"""
        headers_injected = False

        async def _send(message):
            nonlocal headers_injected
            if not headers_injected and message["type"] == "http.response.start":
                message["headers"].extend(
                    [
                        (
                            b"x-ratelimit-remaining",
                            str(result.minute_remaining).encode(),
                        ),
                        (b"x-ratelimit-reset", str(result.reset_after).encode()),
                    ]
                )
                headers_injected = True
            await send(message)

        await self.app(scope, receive, _send)
