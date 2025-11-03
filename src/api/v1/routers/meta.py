from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import discord
from ..dependencies.security import get_current_user
from ..schemas.meta import Channel, TagDetail
from src.core.cache_service import CacheService

cache_service_instance: Optional[CacheService] = None

router = APIRouter(
    prefix="/meta", tags=["元数据"], dependencies=[Depends(get_current_user)]
)


@router.get(
    "/channels", response_model=List[Channel], summary="获取已索引的频道及其可用标签"
)
async def get_indexed_channels_with_tags(
    channel_ids: Optional[List[int]] = Query(
        default=None, description="要查询的特定频道ID列表。"
    ),
):
    if not cache_service_instance:
        raise HTTPException(status_code=503, detail="Cache 服务尚未初始化")

    all_channels: list[discord.ForumChannel] = (
        cache_service_instance.get_indexed_channels()
    )
    target_channels = [
        ch for ch in all_channels if not channel_ids or ch.id in channel_ids
    ]

    response_data = [
        Channel(
            id=channel.id,
            name=channel.name,
            tags=[
                TagDetail(id=tag.id, name=tag.name) for tag in channel.available_tags
            ],
        )
        for channel in target_channels
    ]
    return response_data
