from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.thread_repository import ThreadRepository
from dto.open_graph import (
    OpenGraphAuthorDTO,
    ThreadShareMetadataDTO,
    ThreadShareStatsDTO,
)
from open_graph.image_resolver import OpenGraphImageResolver
from open_graph.metadata_cache import OpenGraphMetadataCache
from open_graph.text_formatter import OpenGraphTextFormatter
from shared.image_url_utils import is_http_url


class ThreadOpenGraphService:
    """生成公开帖子的动态 Open Graph 元数据。"""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        image_resolver: OpenGraphImageResolver,
        metadata_cache: OpenGraphMetadataCache,
        excluded_channel_ids: set[int],
    ):
        self.session_factory = session_factory
        self.image_resolver = image_resolver
        self.metadata_cache = metadata_cache
        self.excluded_channel_ids = excluded_channel_ids

    async def get_share_metadata(self, thread_id: int) -> ThreadShareMetadataDTO | None:
        """返回公开帖子元数据，并仅在没有当前有效图时等待重索引。"""
        # 缓存命中前仍查询主资源，统一隐藏删除、失效、深渊或不存在的帖子。
        async with self.session_factory() as session:
            repository = ThreadRepository(session)
            thread = await repository.get_open_graph_thread(
                thread_id, self.excluded_channel_ids
            )
        if thread is None:
            return None

        cached = await self.metadata_cache.get(
            "thread", thread_id, ThreadShareMetadataDTO
        )
        if cached is not None:
            cached_metadata, source_thread_ids = cached
            if not source_thread_ids or set(source_thread_ids) == {thread_id}:
                return cached_metadata
            await self.metadata_cache.invalidate("thread", thread_id)

        # 首次解析保留后续有效图；只有全部失效时才等待至多配置的秒数。
        selection = await self.image_resolver.select_thread_image(
            thread.thread_id,
            thread.thumbnail_urls,
            wait_for_refresh=True,
        )
        request_refresh_attempted = selection.refresh_attempted
        if selection.should_reload:
            async with self.session_factory() as session:
                repository = ThreadRepository(session)
                reloaded = await repository.get_open_graph_thread(
                    thread_id, self.excluded_channel_ids
                )
            if reloaded is None:
                return None
            thread = reloaded
            selection = await self.image_resolver.select_thread_image(
                thread.thread_id,
                thread.thumbnail_urls,
                wait_for_refresh=False,
            )
            selection.refresh_attempted = (
                request_refresh_attempted or selection.refresh_attempted
            )

        # 所有用户文本在服务层统一清洗，响应不会携带任何内部 ID。
        title = OpenGraphTextFormatter.format(
            thread.title, limit=40, empty_value="未命名"
        )
        author_name = OpenGraphTextFormatter.format(
            thread.author_name, limit=20, empty_value="未命名"
        )
        metadata = ThreadShareMetadataDTO(
            title=title or "未命名",
            description=OpenGraphTextFormatter.format(
                thread.description, limit=200, empty_value=None
            ),
            image_url=selection.image_url,
            author=OpenGraphAuthorDTO(
                display_name=author_name or "未命名",
                avatar_url=(
                    thread.author_avatar_url
                    if is_http_url(thread.author_avatar_url)
                    else None
                ),
            ),
            stats=ThreadShareStatsDTO(
                reaction_count=thread.reaction_count,
                reply_count=thread.reply_count,
                collection_count=thread.collection_count,
            ),
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

        # 发生临期或失效图刷新时不缓存，避免把短命或空图片固化十分钟。
        if not selection.refresh_attempted:
            await self.metadata_cache.set(
                "thread",
                thread_id,
                metadata,
                [thread.thread_id] if selection.image_url else [],
                selection.cache_ttl_limit_seconds,
            )
        return metadata
