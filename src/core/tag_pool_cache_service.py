import logging
from typing import Any

import orjson


logger = logging.getLogger(__name__)


class TagPoolCacheService:
    """缓存无需分页的高频标签池响应，并在故障时静默回源数据库。"""

    _TTL_SECONDS = 3600
    _MAX_VALUE_BYTES = 1024 * 1024
    _SOURCES = (None, "custom")
    _SELECTABLE_BY_SOURCE = {
        None: (True, False),
        "custom": (True,),
    }

    def __init__(self, redis_client=None):
        """复用调用方提供的 Redis 连接；未提供时自动禁用缓存。"""
        self.redis = redis_client

    def key(self, payload: dict[str, Any]) -> str | None:
        """仅为前端实际使用的完整标签池组合生成缓存键。"""
        if (
            payload.get("q", "") != ""
            or payload.get("category") is not None
            or payload.get("include_deleted", False)
        ):
            return None
        source = payload.get("source")
        selectable = payload.get("selectable", True)
        if selectable not in self._SELECTABLE_BY_SOURCE.get(source, ()):
            return None
        visibility = "abyss" if payload.get("_can_view_abyss", False) else "public"
        source_name = source or "all"
        selectable_name = "selectable" if selectable else "managed"
        return f"cache:tag-pool:v1:{visibility}:{source_name}:{selectable_name}"

    async def get(self, payload: dict[str, Any]) -> list[dict] | None:
        """读取并解码命中结果；损坏或不可用时视为未命中。"""
        key = self.key(payload)
        if self.redis is None or key is None:
            return None
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            value = orjson.loads(raw)
            if not isinstance(value, list):
                await self.redis.delete(key)
                return None
            return value
        except Exception:
            logger.warning("读取标签池 Redis 缓存失败，已回源数据库", exc_info=True)
            return None

    async def set(self, payload: dict[str, Any], results: list[dict]) -> None:
        """在大小限制内写入完整结果，避免缓存异常影响主请求。"""
        key = self.key(payload)
        if self.redis is None or key is None:
            return
        try:
            encoded = orjson.dumps(results)
            if len(encoded) > self._MAX_VALUE_BYTES:
                logger.info(
                    "标签池响应超过缓存上限，跳过写入 key=%s bytes=%s",
                    key,
                    len(encoded),
                )
                return
            await self.redis.setex(key, self._TTL_SECONDS, encoded.decode("utf-8"))
        except Exception:
            logger.warning("写入标签池 Redis 缓存失败，已忽略", exc_info=True)

    async def invalidate(self) -> None:
        """删除所有受标签池实体变化影响的固定缓存键。"""
        if self.redis is None:
            return
        keys = []
        for visibility in ("public", "abyss"):
            for source in self._SOURCES:
                for selectable in self._SELECTABLE_BY_SOURCE[source]:
                    keys.append(
                        self.key(
                            {
                                "q": "",
                                "source": source,
                                "selectable": selectable,
                                "include_deleted": False,
                                "_can_view_abyss": visibility == "abyss",
                            }
                        )
                    )
        try:
            await self.redis.delete(*(key for key in keys if key is not None))
        except Exception:
            logger.warning("清除标签池 Redis 缓存失败，将依赖 TTL 恢复", exc_info=True)
