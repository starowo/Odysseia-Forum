import logging
from typing import Optional
from redis.asyncio import Redis, from_url

logger = logging.getLogger(__name__)


class RedisManager:
    """管理全局Redis连接池"""

    _client: Optional[Redis] = None

    @classmethod
    async def init_redis(cls, redis_url: str):
        """初始化Redis客户端池"""
        if not cls._client:
            cls._client = from_url(redis_url, decode_responses=True)
            logger.info("Redis连接池初始化成功")

    @classmethod
    async def close_redis(cls):
        """关闭Redis连接池"""
        if cls._client:
            await cls._client.aclose()
            cls._client = None
            logger.info("Redis连接池已关闭")

    @classmethod
    def get_client(cls) -> Redis:
        """获取Redis客户端实例"""
        if not cls._client:
            raise RuntimeError("Redis尚未初始化")
        return cls._client
