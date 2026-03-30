"""Discord OAuth2 authentication router"""

import json
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from api.v1.utils.jwt_utils import sign_jwt, verify_jwt

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
    if not _AUTH_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务未初始化"
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
            bot_token = _AUTH_CONFIG.get("bot_token")
            member_response = await client.get(
                f"https://discord.com/api/guilds/{_AUTH_CONFIG['guild_id']}/members/{user['id']}",
                headers={"Authorization": f"Bot {bot_token}"},
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

            bot_token = _AUTH_CONFIG.get("bot_token")
            member_response = await client.get(
                f"https://discord.com/api/guilds/{_AUTH_CONFIG['guild_id']}/members/{user['id']}",
                headers={"Authorization": f"Bot {bot_token}"},
            )

            if member_response.status_code != 200:
                return JSONResponse(
                    content={"error": "你不在社区内"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            member = member_response.json()

            role_ids = _AUTH_CONFIG["role_ids"].split(",")
            has_role = any(role_id in member.get("roles", []) for role_id in role_ids)

            if not has_role:
                return JSONResponse(
                    content={"error": "缺少指定身份组"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            token = await sign_jwt(
                {"id": user["id"], "username": user["username"]},
                _AUTH_CONFIG["jwt_secret"],
                7 * 24 * 60 * 60,
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

        except Exception as e:
            logger.error(f"OAuth2 回调处理失败 (dev): {e}")
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
    redirect_response.delete_cookie(key="session", path="/")

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
