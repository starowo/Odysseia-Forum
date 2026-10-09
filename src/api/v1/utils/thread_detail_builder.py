from typing import Any, Dict, List, Optional, Set

from api.v1.schemas.search import AuthorDetail, ThreadDetail
from api.v1.schemas.search.tournament_info import TournamentInfo
from api.v1.schemas.search.latest_update import LatestUpdate
from dto.thread_presentation_context import ThreadPresentationContext
from shared.channel_mapping_utils import ChannelMappingUtils


class ThreadDetailBuilder:
    """
    将 ORM Thread 模型转换为 ThreadDetail 响应模型的工具类。

    处理作者信息嵌套、标签提取、虚拟映射标签计算以及收藏状态标记。
    """

    def __init__(self, channel_mappings_config: Optional[Dict[int, List[Dict]]] = None):
        self.channel_mappings = channel_mappings_config or {}
        self.mapping_utils = ChannelMappingUtils(self.channel_mappings)
        self._global_virtual_tags_map = (
            self.mapping_utils.get_all_channel_virtual_tags_map()
        )

    def build(
        self,
        thread: Any,
        collected_thread_ids: Set[int],
        channel_to_virtual: Optional[Dict[int, List[str]]] = None,
        tournament_thread_map: Optional[Dict[int, List[TournamentInfo]]] = None,
        presentation_context: ThreadPresentationContext | None = None,
    ) -> ThreadDetail:
        """构建单个 ThreadDetail。

        :param thread: 数据库 ORM Thread 对象
        :param collected_thread_ids: 当前用户已收藏的帖子 ID 集合
        :param channel_to_virtual: 可选的自定义频道到虚拟标签映射。
            如果为 None，使用全局映射。
        :param tournament_thread_map: thread_id → 所属赛事书单列表。
            如果为 None，所有帖子视为非参赛帖。
        """
        if channel_to_virtual is None:
            channel_to_virtual = self._global_virtual_tags_map

        matched_virtual = channel_to_virtual.get(thread.channel_id, [])
        t_infos = (tournament_thread_map or {}).get(thread.thread_id, [])

        viewer_flags = (
            presentation_context.viewer_flags.for_thread(thread.thread_id)
            if presentation_context
            else (["collected"] if thread.thread_id in collected_thread_ids else [])
        )
        latest_update = None
        update_dto = (
            presentation_context.latest_updates.get(thread.thread_id)
            if presentation_context
            else None
        )
        if update_dto is not None:
            message_link = None
            if update_dto.message_id is not None:
                message_link = (
                    f"https://discord.com/channels/{thread.guild_id}/"
                    f"{thread.thread_id}/{update_dto.message_id}"
                )
            latest_update = LatestUpdate(
                id=update_dto.id,
                description=update_dto.description,
                version=update_dto.version,
                message_link=message_link,
                source_message_at=update_dto.source_message_at,
                published_at=update_dto.published_at,
            )

        return ThreadDetail(
            custom_tags=presentation_context.custom_tags.get(thread.id, [])
            if presentation_context
            else [],
            thread_id=thread.thread_id,
            guild_id=thread.guild_id,
            channel_id=thread.channel_id,
            title=thread.title,
            author=AuthorDetail.model_validate(thread.author)
            if getattr(thread, "author", None)
            else None,
            created_at=thread.created_at,
            last_active_at=thread.last_active_at,
            reaction_count=thread.reaction_count,
            reply_count=thread.reply_count,
            collection_count=thread.collection_count,
            display_count=thread.display_count,
            first_message_excerpt=thread.first_message_excerpt,
            thumbnail_urls=thread.thumbnail_urls or [],
            tags=[
                tag.name
                for tag in thread.tags
                if presentation_context is not None
                and tag.id in presentation_context.native_tag_ids.get(thread.id, set())
            ]
            if getattr(thread, "tags", None)
            else [],
            virtual_tags=list(set(matched_virtual)),
            collected_flag=thread.thread_id in collected_thread_ids,
            viewer_flags=viewer_flags,
            latest_update=latest_update,
            is_tournament=len(t_infos) > 0,
            tournament_info_list=t_infos,
        )

    def build_list(
        self,
        threads: List[Any],
        collected_thread_ids: Set[int],
        channel_to_virtual: Optional[Dict[int, List[str]]] = None,
        tournament_thread_map: Optional[Dict[int, List[TournamentInfo]]] = None,
        presentation_context: ThreadPresentationContext | None = None,
    ) -> List[ThreadDetail]:
        """批量构建 ThreadDetail 列表。"""
        if channel_to_virtual is None:
            channel_to_virtual = self._global_virtual_tags_map

        return [
            self.build(
                t,
                collected_thread_ids,
                channel_to_virtual,
                tournament_thread_map=tournament_thread_map,
                presentation_context=presentation_context,
            )
            for t in threads
        ]
