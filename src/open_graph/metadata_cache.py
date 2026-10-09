from __future__ import annotations

import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis

from dto.open_graph import OpenGraphMetadataCacheDTO


logger = logging.getLogger(__name__)
MetadataDTO = TypeVar("MetadataDTO", bound=BaseModel)


class OpenGraphMetadataCache:
    """以故障开放方式读写内部 Open Graph 元数据缓存。"""

    KEY_PREFIX = "open_graph:metadata:v2"

    def __init__(self, redis: Redis, ttl_seconds: int = 600):
        self.redis = redis
        self.ttl_seconds = max(1, ttl_seconds)

    async def get(
        self,
        resource_type: str,
        resource_id: int,
        response_model: type[MetadataDTO],
    ) -> tuple[MetadataDTO, list[int]] | None:
        """读取并校验缓存信封，Redis 或数据格式异常时按未命中处理。"""
        cache_key = f"{self.KEY_PREFIX}:{resource_type}:{resource_id}"
        try:
            raw_value = await self.redis.get(cache_key)
            if not raw_value:
                return None
            if isinstance(raw_value, bytes):
                raw_value = raw_value.decode("utf-8")
            envelope = OpenGraphMetadataCacheDTO.model_validate_json(raw_value)
            metadata = response_model.model_validate(envelope.payload)
            return metadata, envelope.source_thread_ids
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, TypeError):
            logger.warning(
                "OG 元数据缓存格式无效，按未命中处理",
                extra={"resource_type": resource_type, "resource_id": resource_id},
            )
            return None
        except Exception:
            logger.warning(
                "OG 元数据缓存读取失败，降级查询数据库",
                extra={"resource_type": resource_type, "resource_id": resource_id},
            )
            return None

    async def set(
        self,
        resource_type: str,
        resource_id: int,
        metadata: BaseModel,
        source_thread_ids: list[int],
        ttl_limit_seconds: int | None,
    ) -> None:
        """按默认值与图片安全窗口的较小值写入缓存。"""
        ttl_seconds = self.ttl_seconds
        if ttl_limit_seconds is not None:
            ttl_seconds = min(ttl_seconds, ttl_limit_seconds)
        if ttl_seconds <= 0:
            return

        cache_key = f"{self.KEY_PREFIX}:{resource_type}:{resource_id}"
        envelope = OpenGraphMetadataCacheDTO(
            payload=metadata.model_dump(mode="json"),
            source_thread_ids=source_thread_ids,
        )
        try:
            await self.redis.set(
                cache_key,
                envelope.model_dump_json(),
                ex=max(1, int(ttl_seconds)),
            )
        except Exception:
            logger.warning(
                "OG 元数据缓存写入失败，响应仍直接返回",
                extra={"resource_type": resource_type, "resource_id": resource_id},
            )

    async def invalidate(self, resource_type: str, resource_id: int) -> None:
        """删除复核失败的缓存且不让 Redis 故障中断数据库重建。"""
        cache_key = f"{self.KEY_PREFIX}:{resource_type}:{resource_id}"
        try:
            await self.redis.delete(cache_key)
        except Exception:
            logger.warning(
                "OG 元数据缓存删除失败，继续从数据库重建",
                extra={"resource_type": resource_type, "resource_id": resource_id},
            )
