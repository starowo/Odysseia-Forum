from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.author_repository import AuthorRepository
from core.thread_repository import ThreadRepository
from dto.open_graph import (
    AuthorShareMetadataDTO,
    AuthorShareStatsDTO,
    OpenGraphLatestWorkDTO,
)
from open_graph.image_resolver import OpenGraphImageResolver
from open_graph.metadata_cache import OpenGraphMetadataCache
from open_graph.text_formatter import OpenGraphTextFormatter
from shared.image_url_utils import is_http_url


class AuthorOpenGraphService:
    """生成仅基于公开作品的作者 Open Graph 元数据。"""

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

    async def get_share_metadata(self, author_id: int) -> AuthorShareMetadataDTO | None:
        """返回作者分享元数据，无公开作品时隐藏作者资源。"""
        # 主资源与公开作品统计先行复核，缓存不能让空作者继续暴露。
        async with self.session_factory() as session:
            author_repository = AuthorRepository(session)
            thread_repository = ThreadRepository(session)
            author = await author_repository.get_open_graph_author(author_id)
            stats = await thread_repository.get_open_graph_author_stats(
                author_id, self.excluded_channel_ids
            )
        if author is None or stats.thread_count == 0:
            return None

        cached = await self.metadata_cache.get(
            "author", author_id, AuthorShareMetadataDTO
        )
        if cached is not None:
            cached_metadata, source_thread_ids = cached
            async with self.session_factory() as session:
                sources_valid = await ThreadRepository(
                    session
                ).are_open_graph_author_sources_valid(
                    author_id,
                    source_thread_ids,
                    self.excluded_channel_ids,
                )
            if sources_valid:
                return cached_metadata
            await self.metadata_cache.invalidate("author", author_id)

        # 最新作品与代表作品独立选择，最新作品不要求拥有图片。
        async with self.session_factory() as session:
            repository = ThreadRepository(session)
            latest_work = await repository.get_open_graph_latest_author_work(
                author_id, self.excluded_channel_ids
            )
            candidates = repository.stream_open_graph_author_works(
                author_id, self.excluded_channel_ids
            )
            selection = await self.image_resolver.select_works(candidates)

        # 代表作品标题和最新作品标题分别执行同一套文本边界规则。
        for work in selection.works:
            work.title = (
                OpenGraphTextFormatter.format(
                    work.title, limit=40, empty_value="未命名"
                )
                or "未命名"
            )
        cleaned_latest = None
        if latest_work is not None:
            cleaned_latest = OpenGraphLatestWorkDTO(
                title=OpenGraphTextFormatter.format(
                    latest_work.title, limit=40, empty_value="未命名"
                )
                or "未命名",
                created_at=latest_work.created_at,
            )
        metadata = AuthorShareMetadataDTO(
            display_name=OpenGraphTextFormatter.format(
                author.display_name, limit=20, empty_value="未命名"
            )
            or "未命名",
            avatar_url=author.avatar_url if is_http_url(author.avatar_url) else None,
            stats=AuthorShareStatsDTO(
                thread_count=stats.thread_count,
                reaction_count=stats.reaction_count,
                reply_count=stats.reply_count,
            ),
            latest_work=cleaned_latest,
            works=selection.works,
            updated_at=author.last_updated,
        )

        # 只缓存没有触发图片刷新且所有 Discord 图片都在安全窗口外的响应。
        if not selection.refresh_attempted:
            await self.metadata_cache.set(
                "author",
                author_id,
                metadata,
                selection.source_thread_ids,
                selection.cache_ttl_limit_seconds,
            )
        return metadata
