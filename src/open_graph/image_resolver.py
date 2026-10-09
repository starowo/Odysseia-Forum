from __future__ import annotations

import logging
import math
from collections.abc import AsyncIterable

from dto.open_graph import (
    OpenGraphImageSelectionDTO,
    OpenGraphWorkCandidateDTO,
    OpenGraphWorkDTO,
    OpenGraphWorksSelectionDTO,
)
from open_graph.reindex_queue import OpenGraphReindexQueue
from shared.image_url_utils import (
    discord_attachment_identity,
    discord_expiry_remaining_seconds,
    image_url_identity,
    is_image_url,
)


logger = logging.getLogger(__name__)


class OpenGraphImageResolver:
    """统一处理分享接口的图片有效期、去重与重索引协调。"""

    def __init__(
        self,
        reindex_queue: OpenGraphReindexQueue,
        refresh_before_expiry_seconds: float,
        sync_wait_timeout_seconds: float,
        max_async_refresh_jobs: int,
    ):
        self.reindex_queue = reindex_queue
        self.refresh_before_expiry_seconds = max(0.0, refresh_before_expiry_seconds)
        self.sync_wait_timeout_seconds = max(0.0, sync_wait_timeout_seconds)
        self.max_async_refresh_jobs = max(0, max_async_refresh_jobs)

    async def select_thread_image(
        self,
        thread_id: int,
        thumbnail_urls: list[str],
        *,
        wait_for_refresh: bool,
    ) -> OpenGraphImageSelectionDTO:
        """按原始顺序选择帖子图片，并在无有效图时按需等待一次刷新。"""
        selected_url: str | None = None
        cache_ttl_limit: int | None = None
        requires_refresh = False

        # 同一帖逐个检查，过期图片不会阻止后面的有效图片成为候选。
        for image_url in thumbnail_urls:
            if not is_image_url(image_url):
                continue
            if discord_attachment_identity(image_url) is None:
                selected_url = image_url
                break
            remaining_seconds = discord_expiry_remaining_seconds(image_url)
            if remaining_seconds is None or remaining_seconds <= 0:
                requires_refresh = True
                continue
            selected_url = image_url
            if remaining_seconds <= self.refresh_before_expiry_seconds:
                requires_refresh = True
            else:
                cache_ttl_limit = max(
                    0,
                    math.floor(remaining_seconds - self.refresh_before_expiry_seconds),
                )
            break

        # 无图帖子不入队；只有确实发现 Discord 失效或临期 URL 才协调 Bot。
        if not requires_refresh:
            return OpenGraphImageSelectionDTO(
                image_url=selected_url,
                cache_ttl_limit_seconds=cache_ttl_limit,
            )
        try:
            job_id = await self.reindex_queue.get_or_enqueue(thread_id)
            refresh_attempted = True
        except Exception:
            logger.warning(
                "OG 图片刷新任务入队失败",
                extra={"thread_id": thread_id},
            )
            return OpenGraphImageSelectionDTO(
                image_url=selected_url,
                refresh_attempted=True,
            )

        # 多图接口和已有有效图的单帖接口都只异步刷新，不等待 Discord。
        if selected_url is not None or not wait_for_refresh or not job_id:
            return OpenGraphImageSelectionDTO(
                image_url=selected_url,
                refresh_attempted=refresh_attempted,
            )
        try:
            result = await self.reindex_queue.wait_for_result(
                job_id, self.sync_wait_timeout_seconds
            )
        except Exception:
            logger.warning(
                "OG 图片刷新结果读取失败",
                extra={"thread_id": thread_id},
            )
            return OpenGraphImageSelectionDTO(refresh_attempted=True)
        return OpenGraphImageSelectionDTO(
            refresh_attempted=True,
            should_reload=bool(result and result.get("status") == "success"),
        )

    async def select_works(
        self,
        candidates: AsyncIterable[OpenGraphWorkCandidateDTO],
        *,
        reserved_image_urls: list[str] | None = None,
    ) -> OpenGraphWorksSelectionDTO:
        """流式扫描候选，返回最多五个有效且图片身份不同的代表作品。"""
        works: list[OpenGraphWorkDTO] = []
        source_thread_ids: list[int] = []
        used_identities = {
            identity
            for url in (reserved_image_urls or [])
            if (identity := image_url_identity(url)) is not None
        }
        queued_thread_ids: set[int] = set()
        refresh_attempted = False
        cache_ttl_limit: int | None = None

        async for candidate in candidates:
            # 每个帖子内部遵循缩略图原顺序，并记录是否遇到应刷新的 Discord URL。
            selected_url: str | None = None
            thread_requires_refresh = False
            selected_ttl_limit: int | None = None
            for image_url in candidate.thumbnail_urls:
                if not is_image_url(image_url):
                    continue
                if discord_attachment_identity(image_url) is None:
                    selected_url = image_url
                    break
                remaining_seconds = discord_expiry_remaining_seconds(image_url)
                if remaining_seconds is None or remaining_seconds <= 0:
                    thread_requires_refresh = True
                    continue
                selected_url = image_url
                if remaining_seconds <= self.refresh_before_expiry_seconds:
                    thread_requires_refresh = True
                else:
                    selected_ttl_limit = max(
                        0,
                        math.floor(
                            remaining_seconds - self.refresh_before_expiry_seconds
                        ),
                    )
                break

            # 一次请求最多为配置数量的不同帖子创建或复用刷新任务。
            if (
                thread_requires_refresh
                and candidate.thread_id not in queued_thread_ids
                and len(queued_thread_ids) < self.max_async_refresh_jobs
            ):
                queued_thread_ids.add(candidate.thread_id)
                refresh_attempted = True
                try:
                    await self.reindex_queue.get_or_enqueue(candidate.thread_id)
                except Exception:
                    logger.warning(
                        "OG 代表作品图片刷新任务入队失败",
                        extra={"thread_id": candidate.thread_id},
                    )

            # 无当前有效图或与封面、已有作品重复时继续流式读取下一个候选。
            selected_identity = image_url_identity(selected_url)
            if selected_url is None or selected_identity in used_identities:
                continue
            assert selected_identity is not None
            used_identities.add(selected_identity)
            works.append(
                OpenGraphWorkDTO(
                    title=candidate.title,
                    image_url=selected_url,
                    reaction_count=candidate.reaction_count,
                    created_at=candidate.created_at,
                )
            )
            source_thread_ids.append(candidate.thread_id)
            if selected_ttl_limit is not None:
                cache_ttl_limit = (
                    selected_ttl_limit
                    if cache_ttl_limit is None
                    else min(cache_ttl_limit, selected_ttl_limit)
                )
            if len(works) >= 5:
                break

        return OpenGraphWorksSelectionDTO(
            works=works,
            source_thread_ids=source_thread_ids,
            refresh_attempted=refresh_attempted,
            cache_ttl_limit_seconds=cache_ttl_limit,
        )
