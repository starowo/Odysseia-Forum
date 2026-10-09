"""Redis OAuth 回调幂等缓存。

总体流程：用 OAuth code 的不可逆指纹作为键，一个短锁负责阻止重复交换 code；
状态缓存先保存不含 access token 的 Discord 用户信息，再保存最终身份组结果。
并发回调可以复用这些状态，因此不会因为二次交换一次性 code 而触发 invalid_grant。
"""

import asyncio
import logging
from typing import Optional

import orjson
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL_SECONDS = 10 * 60
OAUTH_LOCK_TTL_SECONDS = 30


class OAuthCallbackCache:
    """保存 OAuth 回调的安全中间状态并协调重复请求。"""

    def __init__(self, redis_client: Redis):
        """使用现有 Redis 客户端初始化缓存。"""
        self._redis = redis_client

    @staticmethod
    def _state_key(code_fingerprint: str) -> str:
        """生成 OAuth 状态缓存键。"""
        return f"auth:oauth:state:{code_fingerprint}"

    @staticmethod
    def _lock_key(code_fingerprint: str) -> str:
        """生成 OAuth 处理锁缓存键。"""
        return f"auth:oauth:lock:{code_fingerprint}"

    async def get_state(self, code_fingerprint: str) -> Optional[dict]:
        """读取 OAuth 回调已保存的处理状态。"""
        try:
            raw = await self._redis.get(self._state_key(code_fingerprint))
            return orjson.loads(raw) if raw else None
        except Exception:
            logger.warning(
                "读取OAuth幂等缓存失败 code_fingerprint=%s",
                code_fingerprint,
                exc_info=True,
            )
            return None

    async def store_state(self, code_fingerprint: str, state: dict) -> None:
        """保存不含 Discord access token 的 OAuth 处理状态。"""
        # 状态只保留十分钟，覆盖浏览器重复跳转而不长期保存登录材料
        try:
            await self._redis.setex(
                self._state_key(code_fingerprint),
                OAUTH_STATE_TTL_SECONDS,
                orjson.dumps(state).decode(),
            )
        except Exception:
            logger.warning(
                "写入OAuth幂等缓存失败 code_fingerprint=%s",
                code_fingerprint,
                exc_info=True,
            )

    async def acquire_lock(self, code_fingerprint: str, attempt_id: str) -> bool:
        """尝试取得 OAuth code 的单次处理锁。"""
        # Redis 不可用时降级为直接处理，避免缓存故障拖垮全部登录
        try:
            acquired = await self._redis.set(
                self._lock_key(code_fingerprint),
                attempt_id,
                ex=OAUTH_LOCK_TTL_SECONDS,
                nx=True,
            )
            return bool(acquired)
        except Exception:
            logger.warning(
                "获取OAuth幂等锁失败 code_fingerprint=%s，降级为直接处理",
                code_fingerprint,
                exc_info=True,
            )
            return True

    async def release_lock(self, code_fingerprint: str, attempt_id: str) -> None:
        """仅释放由当前请求持有的 OAuth 处理锁。"""
        # Lua 比较锁持有者后再删除，避免误删后续请求取得的新锁
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        end
        return 0
        """
        try:
            await self._redis.eval(
                script, 1, self._lock_key(code_fingerprint), attempt_id
            )
        except Exception:
            logger.warning(
                "释放OAuth幂等锁失败 code_fingerprint=%s",
                code_fingerprint,
                exc_info=True,
            )

    async def wait_for_state(
        self, code_fingerprint: str, timeout_seconds: float = 10.0
    ) -> Optional[dict]:
        """等待并发回调写入可复用的 OAuth 状态。"""
        # 短轮询只发生在同一 code 并发提交时，不影响正常登录流量
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            state = await self.get_state(code_fingerprint)
            if state:
                return state
            await asyncio.sleep(0.1)
        return None
