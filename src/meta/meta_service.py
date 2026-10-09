import logging
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.cache_service import CacheService
from core.thread_repository import ThreadRepository
from dto.meta import (
    TagDetail,
    ChannelDetail,
    VirtualTagDetail,
    MappedSourceChannelDetail,
)

logger = logging.getLogger(__name__)


class MetaService:
    """处理并聚合系统元数据（如频道目录）的服务。"""

    def __init__(
        self,
        session: AsyncSession,
        cache_service: CacheService,
        channel_mappings: Dict[int, List[Dict]],
    ):
        self.session = session
        self.cache_service = cache_service
        self.channel_mappings = channel_mappings

    async def get_channels_meta(
        self, guild_id: Optional[int], channel_ids: Optional[List[int]]
    ) -> List[ChannelDetail]:
        """获取包含标签、虚拟标签及各项帖子数量的频道聚合数据"""

        # 获取全量已索引频道用于建立查找字典
        full_channels_cache = self.cache_service.get_indexed_channels()
        all_channels_dict = {ch.id: ch for ch in full_channels_cache}

        # 筛选本次请求需要展示的目标频道（在这里应用 guild_id 过滤）
        target_channels = []
        for ch in full_channels_cache:
            # 如果指定了 guild_id，过滤掉不属于该服务器的频道
            if guild_id and ch.guild.id != guild_id:
                continue
            # 如果指定了 channel_ids，过滤掉不在列表中的频道
            if channel_ids and ch.id not in channel_ids:
                continue
            target_channels.append(ch)

        if not target_channels:
            return []

        # 收集所有需要查询帖子数的频道ID（包括实际频道和作为映射源的来源频道）
        all_needed_channel_ids: set[int] = set()
        for channel in target_channels:
            all_needed_channel_ids.add(channel.id)
            for mapping in self.channel_mappings.get(channel.id, []):
                all_needed_channel_ids.update(mapping.get("source_channel_ids", []))

        # 从数据库批量查询帖子统计
        thread_repository = ThreadRepository(self.session)
        count_items = await thread_repository.get_thread_count_by_channels(
            list(all_needed_channel_ids)
        )
        counts_map = {item.channel_id: item.thread_count for item in count_items}

        # 组装返回数据
        results: List[ChannelDetail] = []
        for channel in target_channels:
            tags = [
                TagDetail(tag_id=tag.id, name=tag.name)
                for tag in channel.available_tags
            ]
            mappings = self.channel_mappings.get(channel.id, [])

            virtual_tags: List[VirtualTagDetail] = []
            mapped_source_ids: set[int] = set()

            # 解析虚拟标签和提取所有的源频道 ID
            for mapping in mappings:
                if "tag_name" not in mapping:
                    continue

                src_ids = mapping.get("source_channel_ids", [])
                virtual_tags.append(
                    VirtualTagDetail(
                        tag_name=mapping["tag_name"], source_channel_ids=src_ids
                    )
                )
                mapped_source_ids.update(src_ids)

            # 计算实际帖子数
            real_count = counts_map.get(channel.id, 0)

            # 计算虚拟映射源频道的帖子总数
            virtual_count = sum(
                counts_map.get(source_id, 0) for source_id in mapped_source_ids
            )
            total_count = real_count + virtual_count

            # 组装来源频道详细信息列表
            mapped_source_channels: List[MappedSourceChannelDetail] = []
            for src_id in mapped_source_ids:
                src_ch = all_channels_dict.get(src_id)
                if not src_ch:  # 只有该频道已被系统索引且获取到缓存时才计入
                    continue

                src_tags = [
                    TagDetail(tag_id=t.id, name=t.name) for t in src_ch.available_tags
                ]
                mapped_source_channels.append(
                    MappedSourceChannelDetail(
                        guild_id=src_ch.guild.id,
                        channel_id=src_ch.id,
                        channel_name=src_ch.name,
                        available_tags=src_tags,
                        real_thread_count=counts_map.get(src_id, 0),
                    )
                )

            # 获取频道所属类别信息
            category_id = channel.category_id
            category_name = None
            if category_id:
                # 优先直接通过 channel.category 获取类别名
                if channel.category:
                    category_name = channel.category.name
                else:
                    # channel.category 为空时，通过 bot 缓存获取
                    category = self.cache_service.bot.get_channel(category_id)
                    if category:
                        category_name = category.name

            results.append(
                ChannelDetail(
                    guild_id=channel.guild.id,
                    guild_name=channel.guild.name,
                    channel_id=channel.id,
                    name=channel.name,
                    category_id=category_id,
                    category_name=category_name,
                    available_tags=tags,
                    virtual_tags=virtual_tags,
                    mapped_source_channels=mapped_source_channels,
                    real_thread_count=real_count,
                    virtual_thread_count=virtual_count,
                    total_thread_count=total_count,
                )
            )

        return results
