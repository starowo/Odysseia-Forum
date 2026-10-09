"""Discord OAuth2 认证路由。

生产登录分为 OAuth code 交换、Discord 用户读取、服务器成员与身份组验证、JWT
签发四个阶段。OAuth 中间状态存入 Redis 以承接重复回调；成员验证由多 Bot Token
服务完成。checkauth 优先使用成员缓存，Discord 临时不可用时最多沿用 24 小时内
验证过的角色，只有明确失去成员或身份组资格时才删除会话。
"""

import hashlib
import json
import logging
import os
import secrets
import time
from typing import Optional
from urllib.parse import urlencode

import httpx
import orjson
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from api.v1.utils.jwt_utils import sign_jwt, verify_jwt
from core.discord_member_verifier import DiscordMemberVerifier
from core.oauth_callback_cache import OAuthCallbackCache
from shared.enum.constant_enum import ConstantEnum
from shared.redis_client import RedisManager

logger = logging.getLogger(__name__)

# 全局配置变量，将在应用启动时初始化
_AUTH_CONFIG: Optional[dict] = None
_MEMBER_VERIFIER: Optional[DiscordMemberVerifier] = None
_OAUTH_CALLBACK_CACHE: Optional[OAuthCallbackCache] = None

JWT_TTL_SECONDS = 7 * 24 * 60 * 60
ROLE_VERIFICATION_TTL_SECONDS = int(ConstantEnum.AUTH_CACHE_TTL)


def initialize_auth_config():
    """在应用启动时调用，初始化认证配置"""
    global _AUTH_CONFIG, _MEMBER_VERIFIER, _OAUTH_CALLBACK_CACHE
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        auth_config = config.get("auth", {})
        if not auth_config:
            raise ValueError("认证配置 (auth) 未在 config.json 中配置")

        bot_token = os.environ.get("BOT_TOKEN", "").strip()
        if not bot_token:
            raise ValueError("BOT_TOKEN 环境变量未设置")
        # 辅助 Token 只注入 API 认证服务，不改变主 Bot 的网关连接和其他请求
        auxiliary_tokens = [
            token.strip()
            for token in os.environ.get("AUTH_BOT_TOKENS", "").split(",")
            if token.strip()
        ]
        auth_config = {**auth_config, "bot_token": bot_token}

        required_fields = [
            "client_id",
            "client_secret",
            "redirect_uri",
            "guild_id",
            "role_ids",
            "jwt_secret",
            "frontend_url",
        ]

        for field in required_fields:
            if not auth_config.get(field):
                raise ValueError(f"认证配置字段 {field} 未在 config.json 中配置")

        _MEMBER_VERIFIER = DiscordMemberVerifier(
            guild_id=str(auth_config["guild_id"]),
            primary_token=bot_token,
            auxiliary_tokens=auxiliary_tokens,
        )
        _OAUTH_CALLBACK_CACHE = OAuthCallbackCache(RedisManager.get_client())
        _AUTH_CONFIG = auth_config
        logger.info(
            "认证配置已初始化 auth_token_count=%s auth_token_aliases=%s",
            _MEMBER_VERIFIER.token_count,
            ",".join(_MEMBER_VERIFIER.token_aliases),
        )

    except (FileNotFoundError, RuntimeError, ValueError) as e:
        logger.error("无法加载认证配置: %s", e)
        _AUTH_CONFIG = None
        _MEMBER_VERIFIER = None
        _OAUTH_CALLBACK_CACHE = None


async def _get_cached_member(user_id: str) -> Optional[dict]:
    """从 Redis 读取缓存的 Discord 成员信息"""
    try:
        client = RedisManager.get_client()
        cache_key = f"user:discord:{user_id}"
        raw = await client.get(cache_key)
        if raw:
            cached = orjson.loads(raw)
            # 旧缓存没有时间字段时，用 Redis 剩余 TTL 反推出最近验证时间
            if "roles_verified_at" not in cached:
                remaining_ttl = await client.ttl(cache_key)
                if 0 <= remaining_ttl <= ROLE_VERIFICATION_TTL_SECONDS:
                    cached["roles_verified_at"] = time.time() - (
                        ROLE_VERIFICATION_TTL_SECONDS - remaining_ttl
                    )
            return cached
    except Exception:
        logger.warning("读取用户缓存失败", exc_info=True)
    return None


async def _cache_member(user_id: str, member: dict) -> None:
    """只缓存已通过论坛身份组校验的 Discord 成员信息。"""
    roles = [str(role_id) for role_id in member.get("roles", [])]
    if not _has_required_role(roles):
        await _delete_cached_member(user_id, "missing_required_role")
        logger.warning(
            "拒绝写入未授权成员缓存 user_id=%s reason=missing_required_role",
            user_id,
        )
        return

    try:
        client = RedisManager.get_client()
        await client.setex(
            f"user:discord:{user_id}",
            int(ConstantEnum.AUTH_CACHE_TTL),
            orjson.dumps(member).decode(),
        )
    except Exception:
        logger.warning("写入用户缓存失败", exc_info=True)


async def _delete_cached_member(user_id: str, reason: str) -> None:
    """按用户删除可能阻碍后续实时验证的 Discord 成员缓存。"""
    try:
        deleted = await RedisManager.get_client().delete(f"user:discord:{user_id}")
        if deleted:
            logger.info("成员缓存已失效 user_id=%s reason=%s", user_id, reason)
    except Exception:
        logger.warning(
            "删除成员缓存失败 user_id=%s reason=%s",
            user_id,
            reason,
            exc_info=True,
        )


def _get_role_ids() -> list[str]:
    """返回清理后的允许访问身份组 ID。"""
    return [
        role_id.strip()
        for role_id in _AUTH_CONFIG["role_ids"].split(",")
        if role_id.strip()
    ]


def _has_required_role(roles: list[str]) -> bool:
    """判断成员是否具有任一允许访问的身份组。"""
    return any(role_id in roles for role_id in _get_role_ids())


def _roles_verified_at_from_payload(payload: dict) -> float:
    """读取身份组验证时间，并兼容升级前签发的 JWT。"""
    raw_verified_at = payload.get("roles_verified_at")
    if isinstance(raw_verified_at, (int, float)):
        return float(raw_verified_at)

    # 旧 JWT 固定有效七天，可由过期时间保守推算原始签发时间
    raw_exp = payload.get("exp")
    if isinstance(raw_exp, (int, float)):
        return float(raw_exp) - JWT_TTL_SECONDS
    return 0.0


def _is_role_verification_fresh(verified_at: float) -> bool:
    """判断身份组验证结果是否仍在允许的降级时间内。"""
    age_seconds = max(0.0, time.time() - verified_at)
    return verified_at > 0 and age_seconds <= ROLE_VERIFICATION_TTL_SECONDS


async def _get_authorized_cached_member(user_id: str) -> Optional[dict]:
    """只返回新鲜且仍具有论坛访问身份组的成员缓存。"""
    cached = await _get_cached_member(user_id)
    if not cached:
        return None

    # 格式异常的历史值同样不能阻断登录，清理后改走实时查询
    if not isinstance(cached, dict):
        await _delete_cached_member(user_id, "invalid_format")
        return None

    try:
        roles = [str(role_id) for role_id in cached.get("roles", [])]
        verified_at = float(cached.get("roles_verified_at", 0))
    except (TypeError, ValueError):
        await _delete_cached_member(user_id, "invalid_format")
        return None

    # 过期快照不参与认证，本次请求立即转入 Discord 实时验证
    if not _is_role_verification_fresh(verified_at):
        await _delete_cached_member(user_id, "expired")
        return None

    # 历史失败快照不能继续拒绝用户，删除后在本次请求重新验证
    if not _has_required_role(roles):
        await _delete_cached_member(user_id, "cached_missing_required_role")
        return None

    cached["roles"] = roles
    return cached


def _safe_discord_error(
    response: httpx.Response,
) -> tuple[Optional[str], Optional[str]]:
    """从 Discord 响应中读取安全的错误字段。"""
    try:
        payload = response.json()
    except ValueError:
        return None, None
    error = payload.get("error")
    description = payload.get("error_description")
    return (
        str(error)[:100] if error is not None else None,
        str(description)[:200] if description is not None else None,
    )


def _oauth_error_redirect(message: str, error_status: int) -> RedirectResponse:
    """携带安全错误参数直接跳回前端登录页。"""
    frontend_url = _AUTH_CONFIG["frontend_url"].rstrip("/")
    error_query = urlencode({"error": message, "status": error_status})
    return RedirectResponse(url=f"{frontend_url}/login?{error_query}", status_code=302)


def _log_oauth_failure(
    attempt_id: str,
    code_fingerprint: str,
    step: str,
    started_at: float,
    *,
    status_code: Optional[int] = None,
    discord_error: Optional[str] = None,
    user_id: Optional[str] = None,
    token_alias: Optional[str] = None,
    retry_after: Optional[float] = None,
) -> None:
    """记录一条不含凭证的 OAuth 最终失败日志。"""
    logger.error(
        "OAuth登录失败 attempt_id=%s code_fingerprint=%s step=%s status=%s "
        "discord_error=%s user_id=%s token_alias=%s retry_after=%s duration_ms=%s",
        attempt_id,
        code_fingerprint,
        step,
        status_code,
        discord_error,
        user_id,
        token_alias,
        retry_after,
        int((time.monotonic() - started_at) * 1000),
    )


async def _create_login_response(auth_state: dict) -> RedirectResponse:
    """根据已验证的 OAuth 状态签发登录 JWT。"""
    user = auth_state["user"]
    token = await sign_jwt(
        {
            "id": user["id"],
            "username": user["username"],
            "roles": auth_state["roles"],
            "roles_verified_at": auth_state["roles_verified_at"],
        },
        _AUTH_CONFIG["jwt_secret"],
        JWT_TTL_SECONDS,
    )
    response = RedirectResponse(
        url=f"{_AUTH_CONFIG['frontend_url']}#token={token}", status_code=302
    )
    response.set_cookie(
        key="session",
        value=token,
        max_age=JWT_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=True,
        samesite="none",
    )
    return response


router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/login", summary="Discord OAuth2 登录入口")
async def login():
    """重定向到 Discord OAuth2 授权页面"""
    if not _AUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务未初始化"
        )

    params = {
        "client_id": _AUTH_CONFIG["client_id"],
        "redirect_uri": _AUTH_CONFIG["redirect_uri"],
        "response_type": "code",
        "scope": "identify",
    }

    auth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback", summary="Discord OAuth2 回调")
async def callback(code: Optional[str] = None):
    """处理 Discord OAuth2 回调"""
    # 每次 HTTP 回调生成独立编号，code 仅以不可逆短指纹出现在日志和 Redis
    started_at = time.monotonic()
    attempt_id = secrets.token_hex(6)
    if not _AUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务未初始化"
        )

    if not code:
        _log_oauth_failure(
            attempt_id, "missing", "missing_code", started_at, status_code=400
        )
        return _oauth_error_redirect("缺少 Discord 授权代码，请重新登录。", 400)

    code_fingerprint = hashlib.sha256(code.encode()).hexdigest()[:12]
    # 已完成的同 code 回调可以直接重新签发本站 JWT，不再访问 Discord token 接口
    state = (
        await _OAUTH_CALLBACK_CACHE.get_state(code_fingerprint)
        if _OAUTH_CALLBACK_CACHE
        else None
    )
    if state and state.get("stage") == "authenticated":
        return await _create_login_response(state)

    # 首个回调持有短锁，重复回调等待或复用已写入的安全中间状态
    lock_acquired = True
    if _OAUTH_CALLBACK_CACHE:
        lock_acquired = await _OAUTH_CALLBACK_CACHE.acquire_lock(
            code_fingerprint, attempt_id
        )
        if not lock_acquired and not state:
            state = await _OAUTH_CALLBACK_CACHE.wait_for_state(code_fingerprint)
            if not state:
                _log_oauth_failure(
                    attempt_id,
                    code_fingerprint,
                    "duplicate_wait",
                    started_at,
                    status_code=503,
                )
                return _oauth_error_redirect(
                    "同一次授权仍在处理中，请稍后返回登录页面重试。", 503
                )
            if state.get("stage") == "authenticated":
                return await _create_login_response(state)

    try:
        if lock_acquired and _OAUTH_CALLBACK_CACHE:
            latest_state = await _OAUTH_CALLBACK_CACHE.get_state(code_fingerprint)
            if latest_state:
                state = latest_state
            if state and state.get("stage") == "authenticated":
                return await _create_login_response(state)

        # 同一个 HTTP 客户端承载 OAuth 用户查询和成员查询，统一超时边界
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        ) as client:
            # 优先复用已完成 code 交换的安全用户信息
            user = state.get("user") if state else None
            if not user:
                token_data = {
                    "client_id": _AUTH_CONFIG["client_id"],
                    "client_secret": _AUTH_CONFIG["client_secret"],
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": _AUTH_CONFIG["redirect_uri"],
                }
                token_response = await client.post(
                    "https://discord.com/api/oauth2/token",
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                discord_error, error_description = _safe_discord_error(token_response)
                if token_response.status_code != 200:
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "token_exchange",
                        started_at,
                        status_code=token_response.status_code,
                        discord_error=discord_error,
                    )
                    message = (
                        "Discord 授权链接已经失效或被使用过，请重新登录。"
                        if discord_error == "invalid_grant"
                        else "Discord 暂时无法完成授权，请稍后重新登录。"
                    )
                    return _oauth_error_redirect(message, 401)

                try:
                    token_result = token_response.json()
                except ValueError:
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "token_response_json",
                        started_at,
                        status_code=token_response.status_code,
                    )
                    return _oauth_error_redirect(
                        "Discord 返回了无法识别的授权结果，请稍后重试。", 502
                    )

                access_token = token_result.get("access_token")
                if not access_token:
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "token_missing",
                        started_at,
                        status_code=token_response.status_code,
                        discord_error=error_description,
                    )
                    return _oauth_error_redirect(
                        "Discord 没有返回访问凭证，请重新登录。", 502
                    )

                user_response = await client.get(
                    "https://discord.com/api/users/@me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if user_response.status_code != 200:
                    user_error, _ = _safe_discord_error(user_response)
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "user_profile",
                        started_at,
                        status_code=user_response.status_code,
                        discord_error=user_error,
                    )
                    return _oauth_error_redirect(
                        "Discord 用户信息暂时无法读取，请稍后重新登录。", 502
                    )

                try:
                    raw_user = user_response.json()
                except ValueError:
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "user_profile_json",
                        started_at,
                        status_code=user_response.status_code,
                    )
                    return _oauth_error_redirect(
                        "Discord 用户信息格式异常，请稍后重新登录。", 502
                    )

                if not raw_user.get("id") or not raw_user.get("username"):
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "user_profile_missing_fields",
                        started_at,
                        status_code=user_response.status_code,
                    )
                    return _oauth_error_redirect(
                        "Discord 用户信息不完整，请稍后重新登录。", 502
                    )

                user = {
                    "id": str(raw_user["id"]),
                    "username": str(raw_user["username"]),
                    "global_name": raw_user.get("global_name"),
                    "avatar": raw_user.get("avatar"),
                }
                state = {"stage": "oauth_user", "user": user}
                if _OAUTH_CALLBACK_CACHE:
                    await _OAUTH_CALLBACK_CACHE.store_state(code_fingerprint, state)

            # 只有仍具备访问身份组的缓存才能跳过 Discord 实时验证
            cached = await _get_authorized_cached_member(user["id"])
            member_to_cache = None
            if cached:
                roles = [str(role_id) for role_id in cached.get("roles", [])]
                member_user = cached.get("user", {})
                roles_verified_at = float(cached["roles_verified_at"])
            else:
                if not _MEMBER_VERIFIER:
                    raise RuntimeError("Discord 成员验证器未初始化")
                verification = await _MEMBER_VERIFIER.verify_member(
                    user["id"], attempt_id, client
                )
                if verification.outcome == "not_member":
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "guild_member",
                        started_at,
                        status_code=verification.status_code,
                        user_id=user["id"],
                        token_alias=verification.token_alias,
                    )
                    await _delete_cached_member(user["id"], "oauth_not_member")
                    return _oauth_error_redirect(
                        "你的账号目前不在论坛 Discord 服务器中。", 403
                    )
                if verification.outcome == "unavailable":
                    _log_oauth_failure(
                        attempt_id,
                        code_fingerprint,
                        "guild_member_unavailable",
                        started_at,
                        status_code=verification.status_code,
                        user_id=user["id"],
                        token_alias=verification.token_alias,
                        retry_after=verification.retry_after,
                    )
                    return _oauth_error_redirect(
                        "Discord 身份组服务暂时不可用，请稍后返回登录页面重试。", 503
                    )

                member = verification.member or {}
                roles = [str(role_id) for role_id in member.get("roles", [])]
                member_user = member.get("user", {})
                roles_verified_at = time.time()
                member_to_cache = {
                    "roles": roles,
                    "user": member_user,
                    "roles_verified_at": roles_verified_at,
                }

            if not _has_required_role(roles):
                _log_oauth_failure(
                    attempt_id,
                    code_fingerprint,
                    "required_role",
                    started_at,
                    status_code=403,
                    user_id=user["id"],
                )
                await _delete_cached_member(user["id"], "oauth_missing_required_role")
                return _oauth_error_redirect("你的账号缺少访问论坛所需的身份组。", 403)

            # 实时验证完整通过后才写入一天成员缓存
            if member_to_cache:
                await _cache_member(user["id"], member_to_cache)

            # 最终缓存只包含本站签发 JWT 所需信息，不保存 Discord access token
            authenticated_state = {
                "stage": "authenticated",
                "user": user,
                "roles": roles,
                "member_user": member_user,
                "roles_verified_at": roles_verified_at,
            }
            if _OAUTH_CALLBACK_CACHE:
                await _OAUTH_CALLBACK_CACHE.store_state(
                    code_fingerprint, authenticated_state
                )

            return await _create_login_response(authenticated_state)
    except Exception as exc:
        logger.exception(
            "OAuth回调处理异常 attempt_id=%s code_fingerprint=%s exception=%s",
            attempt_id,
            code_fingerprint,
            type(exc).__name__,
        )
        _log_oauth_failure(
            attempt_id,
            code_fingerprint,
            "unexpected_exception",
            started_at,
        )
        return _oauth_error_redirect("认证服务暂时出现异常，请稍后重新登录。", 503)
    finally:
        # 即使中途跳回登录页也释放本请求持有的锁
        if lock_acquired and _OAUTH_CALLBACK_CACHE:
            await _OAUTH_CALLBACK_CACHE.release_lock(code_fingerprint, attempt_id)


def _get_dev_redirect_uri() -> str:
    """将配置中的 redirect_uri 从 /callback 替换为 /callback-dev"""
    base = _AUTH_CONFIG["redirect_uri"]
    if base.endswith("/callback"):
        return base + "-dev"
    return base.rstrip("/") + "-dev"


@router.get("/login-dev", summary="Discord OAuth2 登录入口 (开发用)")
async def login_dev():
    """重定向到 Discord OAuth2 授权页面，回调指向 callback-dev"""
    if not _AUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务未初始化"
        )

    params = {
        "client_id": _AUTH_CONFIG["client_id"],
        "redirect_uri": _get_dev_redirect_uri(),
        "response_type": "code",
        "scope": "identify",
    }

    auth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback-dev", summary="Discord OAuth2 回调 (开发用)")
async def callback_dev(code: Optional[str] = None):
    """处理 Discord OAuth2 回调，直接返回 token HTML 页面而非重定向"""
    attempt_id = f"dev-{secrets.token_hex(6)}"
    if not _AUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务未初始化"
        )

    if not code:
        return JSONResponse(
            content={"error": "缺少授权代码"}, status_code=status.HTTP_400_BAD_REQUEST
        )

    async with httpx.AsyncClient() as client:
        token_data = {
            "client_id": _AUTH_CONFIG["client_id"],
            "client_secret": _AUTH_CONFIG["client_secret"],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _get_dev_redirect_uri(),
        }

        try:
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_result = token_response.json()

            if token_response.status_code != 200:
                logger.error(
                    f"Discord token请求失败 - 状态码: {token_response.status_code}"
                )
                logger.error(f"响应内容: {token_result}")
                error_msg = token_result.get(
                    "error_description", token_result.get("error", "获取访问令牌失败")
                )
                return JSONResponse(
                    content={"error": error_msg},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            if "access_token" not in token_result:
                logger.error(f"Token响应中缺少access_token: {token_result}")
                return JSONResponse(
                    content={"error": "获取访问令牌失败"},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            access_token = token_result["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            user_response = await client.get(
                "https://discord.com/api/users/@me", headers=headers
            )
            user = user_response.json()

            # 开发回调也复用认证 Token 池，避免测试流量集中到主 Bot
            if not _MEMBER_VERIFIER:
                raise RuntimeError("Discord 成员验证器未初始化")
            verification = await _MEMBER_VERIFIER.verify_member(
                str(user["id"]), attempt_id, client
            )
            if verification.outcome == "not_member":
                await _delete_cached_member(str(user["id"]), "oauth_dev_not_member")
                return JSONResponse(
                    content={"error": "你不在社区内"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            if verification.outcome == "unavailable":
                return JSONResponse(
                    content={"error": "Discord身份验证暂时不可用"},
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            member = verification.member or {}

            if not _has_required_role(member.get("roles", [])):
                await _delete_cached_member(
                    str(user["id"]), "oauth_dev_missing_required_role"
                )
                return JSONResponse(
                    content={"error": "缺少指定身份组"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            # 缓存成员信息到 Redis
            roles_verified_at = time.time()
            await _cache_member(
                user["id"],
                {
                    "roles": member.get("roles", []),
                    "user": member.get("user", {}),
                    "roles_verified_at": roles_verified_at,
                },
            )

            token = await sign_jwt(
                {
                    "id": user["id"],
                    "username": user["username"],
                    "roles": member.get("roles", []),
                    "roles_verified_at": roles_verified_at,
                },
                _AUTH_CONFIG["jwt_secret"],
                JWT_TTL_SECONDS,
            )

            frontend_url = _AUTH_CONFIG.get("frontend_url", "")
            html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dev Auth Token</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#1a1a2e;color:#e0e0e0;
display:flex;justify-content:center;align-items:center;min-height:100vh}}
.card{{background:#16213e;border-radius:12px;padding:32px;width:min(480px,90vw);
box-shadow:0 8px 32px rgba(0,0,0,.4)}}
h2{{margin-bottom:8px;color:#a8b2d1}}
.user{{color:#64ffda;margin-bottom:24px;font-size:14px}}
label{{display:block;font-size:13px;color:#8892b0;margin-bottom:6px}}
.token-box{{background:#0a0f1e;border:1px solid #233554;border-radius:8px;padding:10px 12px;
font-family:monospace;font-size:12px;word-break:break-all;color:#64ffda;
margin-bottom:20px;max-height:80px;overflow-y:auto;cursor:pointer;position:relative}}
.token-box:hover::after{{content:'点击复制';position:absolute;top:4px;right:8px;
font-size:11px;color:#8892b0}}
.copied{{color:#ffd700!important}}
input[type=text]{{width:100%;padding:10px 12px;border-radius:8px;border:1px solid #233554;
background:#0a0f1e;color:#e0e0e0;font-size:14px;outline:none;transition:border .2s}}
input[type=text]:focus{{border-color:#64ffda}}
.btn{{display:block;width:100%;margin-top:16px;padding:12px;border:none;border-radius:8px;
background:#64ffda;color:#0a0f1e;font-size:15px;font-weight:600;cursor:pointer;
transition:opacity .2s}}
.btn:hover{{opacity:.85}}
.hint{{font-size:12px;color:#5a6785;margin-top:8px}}
</style>
</head>
<body>
<div class="card">
<h2>认证成功</h2>
<p class="user">{user["username"]} ({user["id"]})</p>
<label>JWT Token</label>
<div class="token-box" id="tokenBox" onclick="copyToken()">{token}</div>
<label for="urlInput">前端地址</label>
<input type="text" id="urlInput" value="{frontend_url}" placeholder="https://example.com">
<button class="btn" onclick="go()">携带 Token 跳转</button>
<p class="hint">跳转格式: URL#token=JWT</p>
</div>
<script>
function copyToken(){{
  navigator.clipboard.writeText("{token}");
  var b=document.getElementById("tokenBox");
  b.classList.add("copied");
  setTimeout(function(){{b.classList.remove("copied")}},1500);
}}
function go(){{
  var url=document.getElementById("urlInput").value.trim();
  if(!url)return alert("请输入前端地址");
  window.location.href=url+"#token={token}";
}}
</script>
</body>
</html>"""
            return HTMLResponse(content=html)

        except Exception as exc:
            logger.exception(
                "OAuth回调处理异常 attempt_id=%s mode=dev exception=%s",
                attempt_id,
                type(exc).__name__,
            )
            return JSONResponse(
                content={"error": "认证过程出错"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@router.get("/logout", summary="退出登录")
async def logout(response: Response):
    """退出登录并清除 session cookie"""
    if not _AUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务未初始化"
        )

    # 清除 cookie 并重定向到前端
    redirect_response = RedirectResponse(
        url=_AUTH_CONFIG["frontend_url"], status_code=302
    )
    redirect_response.delete_cookie(
        key="session", path="/", secure=True, samesite="none"
    )

    return redirect_response


@router.get("/checkauth", summary="检查认证状态")
async def check_auth(request: Request):
    """检查用户认证状态并刷新 token"""
    if not _AUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务未初始化"
        )

    # 从 Authorization header 或 Cookie 中获取 token
    token = None
    token_source = "none"
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        token_source = "bearer"

    if not token:
        cookie = request.cookies.get("session")
        if cookie:
            token = cookie
            token_source = "cookie"

    if not token:
        return JSONResponse(content={"loggedIn": False}, status_code=200)

    # 验证 token
    payload = await verify_jwt(token, _AUTH_CONFIG["jwt_secret"])
    if not payload:
        logger.warning("登录状态验证失败 step=jwt source=%s", token_source)
        return JSONResponse(content={"loggedIn": False}, status_code=200)

    # 只有仍具备访问身份组的缓存才能跳过 Discord 实时验证
    user_id = str(payload["id"])
    attempt_id = secrets.token_hex(6)
    cached = await _get_authorized_cached_member(user_id)
    user_roles = [str(role_id) for role_id in payload.get("roles", [])]
    roles_verified_at = _roles_verified_at_from_payload(payload)
    member_to_cache = None
    user_info = {
        "id": user_id,
        "username": payload.get("username", ""),
        "global_name": None,
        "avatar": None,
    }

    if cached:
        user_roles = [str(role_id) for role_id in cached.get("roles", [])]
        cached_verified_at = cached.get("roles_verified_at")
        if isinstance(cached_verified_at, (int, float)):
            roles_verified_at = float(cached_verified_at)
        user_data = cached.get("user", {})
        user_info = {
            "id": user_data.get("id", user_id),
            "username": user_data.get("username", payload.get("username", "")),
            "global_name": user_data.get("global_name"),
            "avatar": user_data.get("avatar"),
        }
    else:
        if not _MEMBER_VERIFIER:
            logger.error(
                "登录状态验证失败 attempt_id=%s user_id=%s step=verifier_uninitialized",
                attempt_id,
                user_id,
            )
            return JSONResponse(
                content={"loggedIn": False, "error": "身份验证服务未初始化"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 缓存未命中才调用多 Token 验证服务
        verification = await _MEMBER_VERIFIER.verify_member(user_id, attempt_id)
        if verification.outcome == "not_member":
            logger.warning(
                "登录状态验证失败 attempt_id=%s user_id=%s step=guild_member "
                "status=%s action=logout",
                attempt_id,
                user_id,
                verification.status_code,
            )
            await _delete_cached_member(user_id, "checkauth_not_member")
            response = JSONResponse(content={"loggedIn": False}, status_code=200)
            response.delete_cookie(
                key="session", path="/", secure=True, samesite="none"
            )
            return response

        # 临时故障允许使用 24 小时内的 JWT 角色，但不会刷新验证时间
        if verification.outcome == "unavailable":
            if _is_role_verification_fresh(roles_verified_at) and _has_required_role(
                user_roles
            ):
                logger.warning(
                    "登录状态降级成功 attempt_id=%s user_id=%s step=guild_member "
                    "status=%s token_alias=%s roles_age_seconds=%s action=keep_session",
                    attempt_id,
                    user_id,
                    verification.status_code,
                    verification.token_alias,
                    int(max(0.0, time.time() - roles_verified_at)),
                )
            else:
                # 超过安全窗口时返回 503 并保留 Cookie，Discord 恢复后仍可复验
                logger.error(
                    "登录状态验证暂不可用 attempt_id=%s user_id=%s "
                    "step=guild_member status=%s token_alias=%s "
                    "roles_age_seconds=%s action=preserve_session",
                    attempt_id,
                    user_id,
                    verification.status_code,
                    verification.token_alias,
                    int(max(0.0, time.time() - roles_verified_at))
                    if roles_verified_at
                    else None,
                )
                response = JSONResponse(
                    content={"loggedIn": False, "error": "Discord身份验证暂时不可用"},
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
                if verification.retry_after is not None:
                    response.headers["Retry-After"] = str(
                        max(1, int(verification.retry_after))
                    )
                return response
        else:
            # 实时查询完成后先保留结果，身份组校验通过后才允许写缓存
            member = verification.member or {}
            user_roles = [str(role_id) for role_id in member.get("roles", [])]
            roles_verified_at = time.time()
            user_data = member.get("user", {})
            user_info = {
                "id": user_data.get("id", user_id),
                "username": user_data.get("username", payload.get("username", "")),
                "global_name": user_data.get("global_name"),
                "avatar": user_data.get("avatar"),
            }
            member_to_cache = {
                "roles": user_roles,
                "user": member.get("user", user_info),
                "roles_verified_at": roles_verified_at,
            }

    # 校验角色（缓存路径下也需要校验）
    if not _has_required_role(user_roles):
        logger.warning(
            "登录状态验证失败 attempt_id=%s user_id=%s step=required_role action=logout",
            attempt_id,
            user_id,
        )
        await _delete_cached_member(user_id, "checkauth_missing_required_role")
        response = JSONResponse(content={"loggedIn": False}, status_code=200)
        response.delete_cookie(key="session", path="/", secure=True, samesite="none")
        return response

    # 只有本次实时验证成功且身份组合格时才推进成员缓存
    if member_to_cache:
        await _cache_member(user_id, member_to_cache)

    # 获取未读更新数量
    unread_count = 0
    try:
        from shared.database import AsyncSessionFactory
        from core.follow_repository import ThreadFollowRepository

        numeric_user_id = int(user_id)
        async with AsyncSessionFactory() as session:
            follow_service = ThreadFollowRepository(session)
            unread_count = await follow_service.get_unread_count(
                user_id=numeric_user_id
            )
    except Exception:
        logger.exception("获取未读数量失败 user_id=%s", user_id)
        unread_count = 0

    # 刷新 JWT 有效期但继承身份组验证时间，避免临时降级被无限续期
    new_token = await sign_jwt(
        {
            "id": payload["id"],
            "username": payload.get("username", ""),
            "roles": user_roles,
            "roles_verified_at": roles_verified_at,
        },
        _AUTH_CONFIG["jwt_secret"],
        JWT_TTL_SECONDS,
    )

    response = JSONResponse(
        content={"loggedIn": True, "user": user_info, "unread_count": unread_count},
        status_code=200,
    )

    response.set_cookie(
        key="session",
        value=new_token,
        max_age=JWT_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=True,
        samesite="none",
    )

    return response
