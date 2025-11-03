import json
import logging
import sys
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import APIKeyHeader

from ..utils.jwt_utils import verify_jwt

logger = logging.getLogger(__name__)

# 全局变量，在应用启动时初始化
_JWT_SECRET = None


def initialize_api_security():
    """在应用启动时调用，初始化 API 安全配置"""
    global _JWT_SECRET
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        # 加载 JWT 密钥（用于用户认证）
        _JWT_SECRET = config.get("auth", {}).get("jwt_secret")
        if _JWT_SECRET:
            logger.info("JWT 密钥已加载")

        logger.info("API 安全配置已初始化")
    except (FileNotFoundError, ValueError) as e:
        logger.critical(f"严重错误: 无法加载 API 密钥 - {e}")
        logger.critical("程序退出")
        sys.exit(1)


# 定义 API 密钥在请求头中的名称
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    从请求中提取并验证 JWT token，返回用户信息
    优先从 Authorization Bearer 中读取，回退到 Cookie
    """
    if not _JWT_SECRET:
        # 尝试重新加载配置
        initialize_api_security()
        if not _JWT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT 认证服务未初始化",
            )

    # 1) 优先从 Authorization Bearer 中读取
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    # 2) 回退到 Cookie 会话
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
