from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.tag_cache_service import TagCacheService
from core.thread_repository import ThreadRepository
from dto.preferences import UserSearchPreferencesDTO
from models import Tag, Thread
from shared.channel_mapping_utils import ChannelMappingUtils


class BannerThreadVisibilityService:
    """批量过滤当前查看者可见的帖子 Banner。"""

    def __init__(self, session: AsyncSession, tag_cache_service: TagCacheService):
        self.session = session
        self.tag_cache_service = tag_cache_service

    async def get_visible_thread_guilds(
        self,
        thread_ids: list[int],
        prefs: UserSearchPreferencesDTO | None,
        channel_mappings_config: dict[int, list[dict]],
        redis_client=None,
    ) -> dict[int, int]:
        """返回符合公开状态与用户反选偏好的作品及服务器 ID。"""
        if not thread_ids:
            return {}
        effective_prefs = prefs
        channel_ids = None
        if prefs and prefs.exclude_tags:
            repository = ThreadRepository(self.session)
            all_channel_ids = list(await repository.get_all_indexed_channel_ids())
            channel_result = ChannelMappingUtils(channel_mappings_config).resolve(
                channel_ids=None,
                include_tags=[],
                exclude_tags=prefs.exclude_tags,
                tag_logic="or",
                all_indexed_channels=all_channel_ids,
            )
            if channel_result.effective_channel_ids == []:
                return {}
            channel_ids = channel_result.effective_channel_ids
            effective_prefs = prefs.model_copy(
                update={"exclude_tags": channel_result.effective_exclude_tags}
            )

        filters = [
            Thread.thread_id.in_(thread_ids),
            Thread.not_found_count == 0,
            Thread.show_flag.is_(True),
        ]
        if channel_ids is not None:
            filters.append(Thread.channel_id.in_(channel_ids))
        filters.extend(
            await self._build_preference_filters(effective_prefs, redis_client)
        )
        statement = select(Thread.thread_id, Thread.guild_id).where(and_(*filters))
        rows = (await self.session.execute(statement)).all()
        return {thread_id: guild_id for thread_id, guild_id in rows}

    async def _build_preference_filters(
        self,
        prefs: UserSearchPreferencesDTO | None,
        redis_client=None,
    ) -> list:
        """构建 Banner 帖子使用的用户反选过滤条件。"""
        if prefs is None:
            return []
        filters = []
        if prefs.exclude_authors:
            filters.append(Thread.author_id.notin_(prefs.exclude_authors))
        if prefs.exclude_tags:
            excluded_tag_ids = [
                tag_id
                for tag_name in prefs.exclude_tags
                for tag_id in self.tag_cache_service.get_ids_by_tag_name(tag_name)
            ]
            if excluded_tag_ids:
                filters.append(~Thread.tags.any(Tag.id.in_(excluded_tag_ids)))
        if prefs.exclude_keywords:
            result = await ThreadRepository(self.session).get_fts_matched_thread_ids(
                keywords=None,
                exclude_keywords=prefs.exclude_keywords,
                exemption_markers=prefs.exclude_keyword_exemption_markers,
                redis_client=redis_client,
            )
            if result.has_exclude:
                filters.append(~result.exclude_condition)
        return filters
