from typing import Any

from pydantic import BaseModel, Field


class OpenGraphMetadataCacheDTO(BaseModel):
    """描述 Redis 中不会直接暴露给调用方的元数据缓存信封。"""

    payload: dict[str, Any] = Field(description="已序列化的公开响应")
    source_thread_ids: list[int] = Field(
        default_factory=list, description="用于命中复核的来源帖子 ID"
    )
