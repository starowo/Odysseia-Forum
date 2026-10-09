import json
import logging
import sys
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from api.v1.utils.jwt_utils import verify_jwt

logger = logging.getLogger(__name__)

VERIFIED_JWT_PAYLOAD_STATE_KEY = "verified_jwt_payload"

# 全局变量，在应用启动时初始化
_JWT_SECRET = None
_API_KEY = None


def initialize_api_security():
    """在应用启动时调用，初始化 API 安全配置"""
    global _JWT_SECRET, _API_KEY
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        # 加载 JWT 密钥（用于用户认证）
        _JWT_SECRET = config.get("auth", {}).get("jwt_secret")
        if _JWT_SECRET:
            logger.info("JWT 密钥已加载")

        # 加载 API Key（用于BOT机机通信认证）
        _API_KEY = config.get("integration", {}).get("tournament_api_key")
        if _API_KEY:
            logger.info("API Key 已加载")

        logger.info("API 安全配置已初始化")
    except (FileNotFoundError, ValueError) as e:
        logger.critical(f"严重错误: 无法加载 API 密钥 - {e}")
        logger.critical("程序退出")
        sys.exit(1)


# 定义 API 密钥在请求头中的名称
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """
    从请求中提取并验证 JWT token，返回用户信息
    优先从 Authorization Bearer 中读取，回退到 Cookie
    """
    if not _JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT 认证服务未初始化",
        )

    # 复用全局限频中间件已经验证过的 JWT 结果
    request_state = request.scope.get("state", {})
    if VERIFIED_JWT_PAYLOAD_STATE_KEY in request_state:
        return request_state[VERIFIED_JWT_PAYLOAD_STATE_KEY]

    # 优先从 Authorization Bearer 中读取
    token = credentials.credentials if credentials else None

    # 回退到 Cookie 会话
    if not token:
        token = request.cookies.get("session")

    if not token:
        return None

    # 验证 JWT
    payload = await verify_jwt(token, _JWT_SECRET)
    return payload


async def require_auth(
    user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    依赖函数，要求用户必须已认证
    如果未认证则抛出 401 错误
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或会话失效"
        )
    return user


async def require_api_key(
    api_key: Optional[str] = Depends(api_key_header),
) -> bool:
    """验证 X-API-Key 请求头，用于 BOT 机机通信认证"""
    if not _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key 认证未配置",
        )
    if not api_key or api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或缺失的 API Key",
        )
    return True
