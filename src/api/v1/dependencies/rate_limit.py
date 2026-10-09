"""搜索接口频率限制依赖。

按 JWT 中的 user_id 维度限流，Redis 固定窗口算法。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, Response, status

from api.v1.dependencies.security import get_current_user
from dto.rate_limit import RateLimitConfig
from shared.enum.rate_limit_defaults import RateLimitDefaults
from shared.enum.rate_limit_reason import RateLimitReason
from shared.rate_limit import add_watch_reason, check_rate_limit, set_rate_limit_watch
from shared.redis_client import RedisManager

logger = logging.getLogger(__name__)

# 模块级配置，由 initialize_rate_limit() 在启动时设置
_search_config: Optional[RateLimitConfig] = None
_similar_config: Optional[RateLimitConfig] = None


def initialize_rate_limit(config: Optional[dict] = None) -> None:
    """从 config.json 加载搜索接口频率限制配置（启动时调用）。"""
    global _search_config, _similar_config

    raw = (config or {}).get("api", {}).get("rate_limit", {}).get("search", {}) or {}

    _search_config = RateLimitConfig(
        max_requests=raw.get("max_requests", RateLimitDefaults.SEARCH_MAX_REQUESTS),
    )
    similar_raw = (config or {}).get("api", {}).get("rate_limit", {}).get(
        "similar", {}
    ) or {}
    _similar_config = RateLimitConfig(
        max_requests=similar_raw.get(
            "max_requests", RateLimitDefaults.SIMILAR_MAX_REQUESTS
        ),
    )
    logger.info(
        "搜索接口频率限制已初始化: %s次/%s秒",
        _search_config.max_requests,
        _search_config.window_seconds,
    )
    logger.info(
        "相似推荐接口频率限制已初始化: %s次/%s秒",
        _similar_config.max_requests,
        _similar_config.window_seconds,
    )


async def _apply_user_rate_limit(
    *,
    request: Request,
    response: Response,
    current_user: Optional[Dict[str, Any]],
    config: RateLimitConfig | None,
    key_suffix: str,
    include_body: bool = False,
) -> None:
    """执行按用户固定窗口限流。"""
    if config is None:
        return
    user_id = current_user.get("id") if current_user else None
    if not user_id:
        return

    redis = RedisManager.get_client()
    result = await check_rate_limit(
        redis=redis,
        key=f"{config.key_prefix}:{key_suffix}:{user_id}",
        max_requests=config.max_requests,
        window_seconds=config.window_seconds,
    )
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(result.reset_after)
    if result.allowed:
        return

    body = None
    if include_body:
        try:
            raw_body = await request.body()
            body = (
                raw_body.decode("utf-8", errors="replace")[
                    : int(RateLimitDefaults.LOG_BODY_MAX_CHARS)
                ]
                if raw_body
                else "-"
            )
        except Exception:
            body = "-"

    reason = (
        RateLimitReason.SEARCH_RATE_LIMIT
        if key_suffix == "search"
        else RateLimitReason.SIMILAR_RATE_LIMIT
    )
    add_watch_reason(
        request.scope,
        reason,
        body,
        current_count=result.current_count,
        max_requests=config.max_requests,
        reset_after=result.reset_after,
    )
    await set_rate_limit_watch(redis, str(user_id))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="请求过于频繁，请稍后重试",
        headers={"Retry-After": str(result.reset_after)},
    )


async def similar_rate_limit(
    request: Request,
    response: Response,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> None:
    """对相似推荐接口按 user_id 进行独立频率限制。"""
    await _apply_user_rate_limit(
        request=request,
        response=response,
        current_user=current_user,
        config=_similar_config,
        key_suffix="similar",
    )


async def search_rate_limit(
    request: Request,
    response: Response,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> None:
    """对搜索接口按 user_id 进行频率限制。

    作为 router 级 ``Depends`` 使用，配合 ``require_auth`` 确保用户已认证。
    ``get_current_user`` 在同一请求中只会执行一次（FastAPI 依赖缓存）。

    Raises:
        HTTPException(429): 超出频率限制时，附带 Retry-After 头。
    """
    await _apply_user_rate_limit(
        request=request,
        response=response,
        current_user=current_user,
        config=_search_config,
        key_suffix="search",
        include_body=True,
    )
