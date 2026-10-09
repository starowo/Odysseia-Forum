import logging
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from api.v1.schemas.tags import (
    ChannelTagInfo,
    TagStatItem,
    TagStatsRequest,
    TagStatsResponse,
)
from shared.enum.tag_category import TagCategory
from core.thread_repository import ThreadRepository
from core.cache_service import CacheService
from models import Tag, Thread, TagBinding

logger = logging.getLogger(__name__)


class TagStatisticsService:
    """处理标签聚合与统计等复杂跨表业务逻辑的服务。"""

    def __init__(
        self,
        session: AsyncSession,
        cache_service: CacheService,
        channel_mappings: Dict[int, List[Dict]],
    ):
        """
        初始化标签服务。
        """
        self.session = session
        self.cache_service = cache_service
        self.channel_mappings = channel_mappings

    def _get_channel_meta(
        self, channel_id: int
    ) -> Tuple[int, str, str, Optional[int], Optional[str]]:
        """从内存缓存中获取服务器ID、服务器名称、频道名称、类别ID和类别名称"""
        channel = self.cache_service.indexed_channels.get(channel_id)
        if not channel:
            channel = self.cache_service.bot.get_channel(channel_id)

        if channel:
            guild_id = channel.guild.id
            guild_name = channel.guild.name
            c_name = channel.name
            cat_id = channel.category_id
            cat_name = None

            # 处理属性 category 为 None 的情况
            if cat_id:
                # 显式从缓存中获取分类对象
                category = self.cache_service.bot.get_channel(cat_id)
                if category:
                    cat_name = category.name

            return guild_id, guild_name, c_name, cat_id, cat_name

        return 0, "未知服务器", "未知频道", None, None

    async def aggregate_tag_stats(
        self, request: TagStatsRequest, *, can_view_abyss: bool = False
    ) -> TagStatsResponse:
        """聚合计算标签统计信息"""
        # 先确定请求中的目标频道范围
        requested_channels = set(request.channel_ids) if request.channel_ids else None
        extended_channel_ids = (
            set(request.channel_ids) if request.channel_ids else set()
        )

        # 若包含虚拟标签，则补充映射源频道进入查询范围
        if request.include_virtual and request.channel_ids:
            for channel_id in request.channel_ids:
                for mapping in self.channel_mappings.get(channel_id, []):
                    extended_channel_ids.update(mapping.get("source_channel_ids", []))

        scoped_channel_ids = (
            list(extended_channel_ids) if extended_channel_ids else None
        )

        # 批量查询真实标签在各频道下的聚合结果
        real_tag_rows = await self._get_real_tag_rows(
            request.guild_id, scoped_channel_ids, can_view_abyss=can_view_abyss
        )

        tag_buckets = defaultdict(lambda: {"total": 0, "channels": [], "ids": set()})
        for name, source, category, is_abyss, channel_id, count, ids in real_tag_rows:
            if requested_channels is not None and channel_id not in requested_channels:
                continue
            key = (min(ids), source, category, is_abyss, name)
            bucket = tag_buckets[key]
            bucket["total"] += count
            bucket["ids"].update(ids)
            guild_id, guild_name, channel_name, cat_id, cat_name = (
                self._get_channel_meta(channel_id)
            )
            bucket["channels"].append(
                ChannelTagInfo(
                    guild_id=guild_id,
                    guild_name=guild_name,
                    channel_id=channel_id,
                    channel_name=channel_name,
                    category_id=cat_id,
                    category_name=cat_name,
                    tag_id=min(ids),
                    tag_ids=[str(v) for v in sorted(ids)],
                    thread_count=count,
                    is_virtual=False,
                )
            )
        virtual_buckets = defaultdict(lambda: {"total": 0, "channels": []})
        if request.include_virtual:
            await self._append_virtual_tag_stats(virtual_buckets, request)

        # 统计当前查询范围内的有效帖子总数
        thread_repository = ThreadRepository(self.session)
        total_threads = await thread_repository.get_total_thread_count_for_scope(
            guild_id=request.guild_id,
            channel_ids=scoped_channel_ids,
        )

        items = [
            TagStatItem(
                tag_name=name,
                is_abyss=is_abyss,
                source=source,
                category=category,
                category_name=TagCategory(category).name if category else None,
                tag_ids=[str(v) for v in sorted(data["ids"])],
                total_thread_count=data["total"],
                channel_info=data["channels"],
            )
            for (_, source, category, is_abyss, name), data in tag_buckets.items()
        ]
        items.extend(
            TagStatItem(
                tag_name=name,
                is_abyss=False,
                source="virtual",
                total_thread_count=data["total"],
                channel_info=data["channels"],
            )
            for name, data in virtual_buckets.items()
            if data["channels"]
        )
        items.sort(key=lambda item: (-item.total_thread_count, item.tag_name))
        return TagStatsResponse(total_threads=total_threads, items=items)

    async def _get_real_tag_rows(
        self, guild_id, channel_ids, *, can_view_abyss: bool
    ):
        """按来源、分类、名称和频道聚合有效绑定，并对同组帖子去重。"""
        statement = (
            select(
                Tag.name,
                Tag.source,
                Tag.category,
                Tag.is_abyss,
                Thread.channel_id,
                func.count(func.distinct(Thread.id)),
                func.array_agg(func.distinct(Tag.id)),
            )
            .select_from(TagBinding)
            .join(Tag, Tag.id == TagBinding.tag_id)
            .join(Thread, Thread.id == TagBinding.target_id)
            .where(
                TagBinding.target_type == "thread",
                TagBinding.ended_at.is_(None),
                Tag.deleted_at.is_(None),
                Thread.not_found_count == 0,
                Thread.show_flag.is_(True),
            )
            .group_by(
                Tag.id,
                Tag.name,
                Tag.source,
                Tag.category,
                Tag.is_abyss,
                Thread.channel_id,
            )
        )
        if not can_view_abyss:
            statement = statement.where(Tag.is_abyss.is_(False))
        if guild_id is not None:
            statement = statement.where(Thread.guild_id == guild_id)
        if channel_ids:
            statement = statement.where(Thread.channel_id.in_(channel_ids))
        return (await self.session.execute(statement)).all()

    async def _append_virtual_tag_stats(
        self,
        tag_buckets: Dict[str, Dict[str, Any]],
        request: TagStatsRequest,
    ) -> None:
        """根据频道映射追加虚拟标签统计"""
        thread_repository = ThreadRepository(self.session)
        all_source_ids: set[int] = set()

        # 确定本次需要返回的目标频道集合
        target_channels = (
            request.channel_ids
            if request.channel_ids
            else list(self.channel_mappings.keys())
        )

        # 先收集所有会被虚拟标签引用的源频道
        for target_channel_id in target_channels:
            for mapping in self.channel_mappings.get(target_channel_id, []):
                all_source_ids.update(mapping.get("source_channel_ids", []))

        # 批量查询所有源频道的帖子数
        channel_counts = await thread_repository.get_thread_count_by_channels(
            list(all_source_ids)
        )
        counts_map = {item.channel_id: item.thread_count for item in channel_counts}

        # 逐个目标频道累加其虚拟标签统计
        for target_channel_id in target_channels:
            mappings = self.channel_mappings.get(target_channel_id, [])

            # 获取虚拟标签挂载的目标频道的元数据（如"男性向"频道的分类信息）
            guild_id, guild_name, channel_name, category_id, category_name = (
                self._get_channel_meta(target_channel_id)
            )

            for mapping in mappings:
                tag_name = mapping.get("tag_name")
                source_channel_ids = mapping.get("source_channel_ids", [])

                if not tag_name or not source_channel_ids:
                    continue

                # 虚拟标签值等于所有源频道帖子数之和
                virtual_count = sum(
                    counts_map.get(source_channel_id, 0)
                    for source_channel_id in source_channel_ids
                )
                if virtual_count <= 0:
                    continue

                # 将虚拟标签结果写回聚合桶
                tag_buckets[tag_name]["total"] += virtual_count
                tag_buckets[tag_name]["channels"].append(
                    ChannelTagInfo(
                        guild_id=guild_id,
                        guild_name=guild_name,
                        channel_id=target_channel_id,
                        channel_name=channel_name,
                        category_id=category_id,
                        category_name=category_name,
                        tag_id=0,
                        thread_count=virtual_count,
                        is_virtual=True,
                    )
                )
