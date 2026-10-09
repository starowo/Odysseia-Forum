from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.author_repository import AuthorRepository
from core.booklist_item_repository import BooklistItemRepository
from core.booklist_repository import BooklistRepository
from dto.open_graph import BooklistShareMetadataDTO, BooklistShareStatsDTO
from open_graph.image_resolver import OpenGraphImageResolver
from open_graph.metadata_cache import OpenGraphMetadataCache
from open_graph.text_formatter import OpenGraphTextFormatter
from shared.image_url_utils import is_http_url


class BooklistOpenGraphService:
    """生成公开书单或赛事的多作品 Open Graph 元数据。"""

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

    async def get_share_metadata(
        self, booklist_id: int
    ) -> BooklistShareMetadataDTO | None:
        """返回公开书单元数据，空书单仍返回统计为零的成功响应。"""
        # 缓存命中前查询公开主资源，私有与不存在书单保持同一 404 语义。
        async with self.session_factory() as session:
            booklist = await BooklistRepository(session).get_open_graph_booklist(
                booklist_id
            )
        if booklist is None:
            return None

        cached = await self.metadata_cache.get(
            "booklist", booklist_id, BooklistShareMetadataDTO
        )
        if cached is not None:
            cached_metadata, source_thread_ids = cached
            async with self.session_factory() as session:
                sources_valid = await BooklistItemRepository(
                    session
                ).are_open_graph_sources_valid(
                    booklist_id,
                    source_thread_ids,
                    self.excluded_channel_ids,
                )
            if sources_valid:
                return cached_metadata
            await self.metadata_cache.invalidate("booklist", booklist_id)

        # 非匿名书单单独查询作者；作者记录缺失时按契约返回 null。
        author_name: str | None = None
        if not booklist.is_anonymous:
            async with self.session_factory() as session:
                owner = await AuthorRepository(session).get_open_graph_author(
                    booklist.owner_id
                )
            if owner is not None:
                author_name = OpenGraphTextFormatter.format(
                    owner.display_name, limit=20, empty_value="未命名"
                )

        # 自定义封面只校验完整 HTTP(S)，不解析 Discord 签名且参与作品去重。
        cover_image_url = (
            booklist.cover_image_url if is_http_url(booklist.cover_image_url) else None
        )
        async with self.session_factory() as session:
            item_repository = BooklistItemRepository(session)
            visible_item_count = await item_repository.count_open_graph_visible_items(
                booklist_id, self.excluded_channel_ids
            )
            candidates = item_repository.stream_open_graph_works(
                booklist_id, self.excluded_channel_ids
            )
            selection = await self.image_resolver.select_works(
                candidates,
                reserved_image_urls=[cover_image_url] if cover_image_url else [],
            )

        # 公开响应只包含展示字段，候选来源帖子 ID 仅留在缓存信封内。
        for work in selection.works:
            work.title = (
                OpenGraphTextFormatter.format(
                    work.title, limit=40, empty_value="未命名"
                )
                or "未命名"
            )
        metadata = BooklistShareMetadataDTO(
            title=OpenGraphTextFormatter.format(
                booklist.title, limit=40, empty_value="未命名"
            )
            or "未命名",
            description=OpenGraphTextFormatter.format(
                booklist.description, limit=200, empty_value=None
            ),
            cover_image_url=cover_image_url,
            author_name=author_name,
            works=selection.works,
            stats=BooklistShareStatsDTO(
                item_count=visible_item_count,
                collection_count=booklist.collection_count,
                view_count=booklist.view_count,
            ),
            is_tournament=booklist.is_tournament,
            created_at=booklist.created_at,
            updated_at=booklist.updated_at,
        )

        # 自定义封面沿用直接返回策略，不影响作品图片的缓存安全窗口。
        if not selection.refresh_attempted:
            await self.metadata_cache.set(
                "booklist",
                booklist_id,
                metadata,
                selection.source_thread_ids,
                selection.cache_ttl_limit_seconds,
            )
        return metadata
