"""请求级 Watch 轨迹状态工具。"""

from typing import Any, MutableMapping

from dto.rate_limit import RateLimitTriggerDetail

WATCH_REASONS_STATE_KEY = "rate_limit_watch_reasons"
WATCH_BODY_STATE_KEY = "rate_limit_watch_body"
WATCH_TRIGGER_DETAILS_STATE_KEY = "rate_limit_watch_trigger_details"


def add_watch_reason(
    scope: MutableMapping[str, Any],
    reason: str,
    body: str | None = None,
    *,
    current_count: int | None = None,
    max_requests: int | None = None,
    reset_after: int | None = None,
) -> None:
    """为当前请求登记 Watch 原因、请求体和限频详情。"""
    state = scope.setdefault("state", {})
    reasons = state.setdefault(WATCH_REASONS_STATE_KEY, [])
    if reason not in reasons:
        reasons.append(reason)
    if body is not None and WATCH_BODY_STATE_KEY not in state:
        state[WATCH_BODY_STATE_KEY] = body
    if None not in (current_count, max_requests, reset_after):
        details = state.setdefault(WATCH_TRIGGER_DETAILS_STATE_KEY, {})
        details[reason] = RateLimitTriggerDetail(
            current_count=int(current_count),
            max_requests=int(max_requests),
            reset_after=int(reset_after),
        )


def get_watch_reasons(scope: MutableMapping[str, Any]) -> list[str]:
    """读取当前请求登记的 Watch 原因。"""
    state = scope.get("state", {})
    return list(state.get(WATCH_REASONS_STATE_KEY, []))


def get_watch_body(scope: MutableMapping[str, Any]) -> str | None:
    """读取当前请求登记的请求体。"""
    state = scope.get("state", {})
    body = state.get(WATCH_BODY_STATE_KEY)
    return body if isinstance(body, str) else None


def get_watch_trigger_details(
    scope: MutableMapping[str, Any],
) -> dict[str, RateLimitTriggerDetail]:
    """读取当前请求各触发来源的限频详情。"""
    state = scope.get("state", {})
    details = state.get(WATCH_TRIGGER_DETAILS_STATE_KEY, {})
    return dict(details) if isinstance(details, dict) else {}
