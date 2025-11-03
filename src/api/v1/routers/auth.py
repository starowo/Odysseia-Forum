"""Discord OAuth2 authentication router"""

import json
import logging
from typing import Optional
from urllib.parse import urlencode
from fastapi import APIRouter, Request, HTTPException, status, Response
from fastapi.responses import RedirectResponse, JSONResponse
import httpx

from ..utils.jwt_utils import sign_jwt, verify_jwt

logger = logging.getLogger(__name__)

# 全局配置变量，将在应用启动时初始化
_AUTH_CONFIG: Optional[dict] = None


def initialize_auth_config():
    """在应用启动时调用，初始化认证配置"""
    global _AUTH_CONFIG
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        auth_config = config.get("auth", {})
        if not auth_config:
            raise ValueError("认证配置 (auth) 未在 config.json 中配置")

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

        _AUTH_CONFIG = auth_config
        logger.info("认证配置已初始化")

    except (FileNotFoundError, ValueError) as e:
        logger.error(f"无法加载认证配置: {e}")
        _AUTH_CONFIG = None


router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/login", summary="Discord OAuth2 登录入口")
async def login():
    """重定向到 Discord OAuth2 授权页面"""
    if not _AUTH_CONFIG:
        initialize_auth_config()
        if not _AUTH_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务未初始化"
            )
    
    params = {
        "client_id": _AUTH_CONFIG["client_id"],
        "redirect_uri": _AUTH_CONFIG["redirect_uri"],
        "response_type": "code",
        "scope": "identify guilds.members.read"
    }

    auth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback", summary="Discord OAuth2 回调")
async def callback(code: Optional[str] = None):
    """处理 Discord OAuth2 回调"""
    if not _AUTH_CONFIG:
        initialize_auth_config()
        if not _AUTH_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务未初始化"
            )
    
    if not code:
        error_url = f"{_AUTH_CONFIG['frontend_url']}?error=缺少授权代码"
        return RedirectResponse(url=error_url, status_code=302)

    async with httpx.AsyncClient() as client:
        # 获取 access_token
        token_data = {
            "client_id": _AUTH_CONFIG["client_id"],
            "client_secret": _AUTH_CONFIG["client_secret"],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _AUTH_CONFIG["redirect_uri"],
        }

        try:
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_result = token_response.json()

            # 记录详细的错误信息以便调试
            if token_response.status_code != 200:
                logger.error(
                    f"Discord token请求失败 - 状态码: {token_response.status_code}"
                )
                logger.error(f"响应内容: {token_result}")
                logger.error(f"使用的redirect_uri: {_AUTH_CONFIG['redirect_uri']}")
                error_msg = token_result.get(
                    "error_description", token_result.get("error", "获取访问令牌失败")
                )
                error_url = f"{_AUTH_CONFIG['frontend_url']}?error={error_msg}"
                return RedirectResponse(url=error_url, status_code=302)

            if "access_token" not in token_result:
                logger.error(f"Token响应中缺少access_token: {token_result}")
                error_url = f"{_AUTH_CONFIG['frontend_url']}?error=获取访问令牌失败"
                return RedirectResponse(url=error_url, status_code=302)

            access_token = token_result["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            # 获取用户信息
            user_response = await client.get(
                "https://discord.com/api/users/@me", headers=headers
            )
            user = user_response.json()

            # 验证用户是否在服务器中
            member_response = await client.get(
                f"https://discord.com/api/users/@me/guilds/{_AUTH_CONFIG['guild_id']}/member",
                headers=headers
            )
            
            if member_response.status_code != 200:
                error_url = f"{_AUTH_CONFIG['frontend_url']}?error=你不在社区内"
                return RedirectResponse(url=error_url, status_code=302)

            member = member_response.json()

            # 验证身份组
            role_ids = _AUTH_CONFIG["role_ids"].split(",")
            has_role = any(role_id in member.get("roles", []) for role_id in role_ids)

            if not has_role:
                error_url = f"{_AUTH_CONFIG['frontend_url']}?error=缺少指定身份组"
                return RedirectResponse(url=error_url, status_code=302)

            # 签发 JWT
            token = await sign_jwt(
                {"id": user["id"], "username": user["username"]},
                _AUTH_CONFIG["jwt_secret"],
                7 * 24 * 60 * 60,  # 7天
            )

            # 设置 Cookie
            cookie_domain = _AUTH_CONFIG.get("cookie_domain", "")
            cookie_domain_attr = f"; Domain={cookie_domain}" if cookie_domain else ""

            response = RedirectResponse(
                url=f"{_AUTH_CONFIG['frontend_url']}#token={token}", status_code=302
            )

            response.set_cookie(
                key="session",
                value=token,
                max_age=7 * 24 * 60 * 60,
                path="/",
                httponly=True,
                secure=True,
                samesite="none",
            )

            return response

        except Exception as e:
            logger.error(f"OAuth2 回调处理失败: {e}")
            error_url = f"{_AUTH_CONFIG['frontend_url']}?error=认证过程出错"
            return RedirectResponse(url=error_url, status_code=302)


@router.get("/logout", summary="退出登录")
async def logout(response: Response):
    """退出登录并清除 session cookie"""
    if not _AUTH_CONFIG:
        initialize_auth_config()
        if not _AUTH_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务未初始化"
            )
    
    # 清除 cookie 并重定向到前端
    redirect_response = RedirectResponse(
        url=_AUTH_CONFIG["frontend_url"], status_code=302
    )
    redirect_response.delete_cookie(key="session", path="/")

    return redirect_response


@router.get("/checkauth", summary="检查认证状态")
async def check_auth(request: Request):
    """检查用户认证状态并刷新 token"""
    if not _AUTH_CONFIG:
        initialize_auth_config()
        if not _AUTH_CONFIG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务未初始化"
            )
    
    # 从 Authorization header 或 Cookie 中获取 token
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token:
        cookie = request.cookies.get("session")
        if cookie:
            token = cookie

    if not token:
        return JSONResponse(content={"loggedIn": False}, status_code=200)

    # 验证 token
    payload = await verify_jwt(token, _AUTH_CONFIG["jwt_secret"])
    if not payload:
        return JSONResponse(content={"loggedIn": False}, status_code=200)

    # 使用 Bot Token 再次验证 Discord 身份并获取完整用户信息
    bot_token = _AUTH_CONFIG.get("bot_token")
    user_info = {
        "id": payload["id"],
        "username": payload.get("username", ""),
        "global_name": None,
        "avatar": None,
    }

    if bot_token:
        try:
            async with httpx.AsyncClient() as client:
                member_response = await client.get(
                    f"https://discord.com/api/guilds/{_AUTH_CONFIG['guild_id']}/members/{payload['id']}",
                    headers={"Authorization": f"Bot {bot_token}"},
                )

                if member_response.status_code != 200:
                    response = JSONResponse(
                        content={"loggedIn": False}, status_code=200
                    )
                    response.delete_cookie(key="session", path="/")
                    return response

                member = member_response.json()
                role_ids = _AUTH_CONFIG["role_ids"].split(",")
                has_role = any(
                    role_id in member.get("roles", []) for role_id in role_ids
                )

                if not has_role:
                    response = JSONResponse(
                        content={"loggedIn": False}, status_code=200
                    )
                    response.delete_cookie(key="session", path="/")
                    return response

                # 获取完整的用户信息
                if "user" in member:
                    user_data = member["user"]
                    user_info = {
                        "id": user_data.get("id", payload["id"]),
                        "username": user_data.get(
                            "username", payload.get("username", "")
                        ),
                        "global_name": user_data.get("global_name"),
                        "avatar": user_data.get("avatar"),
                    }

        except Exception as e:
            logger.error(f"验证 Discord 身份失败: {e}")

    # 获取未读更新数量
    unread_count = 0
    try:
        from shared.database import AsyncSessionFactory
        from ThreadManager.services.follow_service import FollowService

        user_id = int(payload["id"])
        async with AsyncSessionFactory() as session:
            follow_service = FollowService(session)
            unread_count = await follow_service.get_unread_count(user_id=user_id)
    except Exception as e:
        logger.error(f"获取未读数量失败: {e}")
        unread_count = 0

    # 刷新 token
    new_token = await sign_jwt(
        {"id": payload["id"], "username": payload.get("username", "")},
        _AUTH_CONFIG["jwt_secret"],
        7 * 24 * 60 * 60,
    )

    response = JSONResponse(
        content={"loggedIn": True, "user": user_info, "unread_count": unread_count},
        status_code=200,
    )

    response.set_cookie(
        key="session",
        value=new_token,
        max_age=7 * 24 * 60 * 60,
        path="/",
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return response
