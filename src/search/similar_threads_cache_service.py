import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from dto.search import SimilarThreadCandidateDTO, SimilarThreadCandidatePoolDTO
from search.similar_threads_busy_error import SimilarThreadsBusyError
from shared.similar_threads_cache import get_similar_candidates_cache_key

logger = logging.getLogger(__name__)

CandidateBuilder = Callable[[], Awaitable[tuple[list[SimilarThreadCandidateDTO], bool]]]


class SimilarThreadsCacheService:
    """管理相似帖子共享候选池、软刷新与同 Key 请求合并。"""

    CANDIDATE_LIMIT = 200
    """每个源帖最多缓存的候选帖子数量。"""

    CACHE_TTL_SECONDS = 3 * 60 * 60
    """非空候选池的 Redis 硬过期时间，单位为秒。"""

    EMPTY_CACHE_TTL_SECONDS = 10 * 60
    """空候选池的 Redis 过期时间，单位为秒。"""

    SOFT_REFRESH_SECONDS = 60 * 60
    """候选池触发后台软刷新的数据年龄，单位为秒。"""

    COLD_QUERY_WAIT_SECONDS = 2.0
    """冷查询等待全局并发名额的最长时间，单位为秒。"""

    def __init__(self, redis_client, cold_query_concurrency: int = 4):
        self._redis = redis_client
        self._cold_query_semaphore = asyncio.Semaphore(cold_query_concurrency)
        self._tasks: dict[str, asyncio.Task[SimilarThreadCandidatePoolDTO | None]] = {}
        self._tasks_lock = asyncio.Lock()

    async def get_or_build(
        self,
        thread_id: int,
        include_abyss: bool,
        builder: CandidateBuilder,
    ) -> SimilarThreadCandidatePoolDTO:
        """读取候选池；硬未命中时合并冷构建，软过期时异步刷新。"""
        key = get_similar_candidates_cache_key(thread_id, include_abyss)
        cached = await self._read_cache(key)
        if cached is not None:
            age = time.time() - cached.generated_at
            if cached.candidates and age >= self.SOFT_REFRESH_SECONDS:
                asyncio.create_task(self._schedule_soft_refresh(key, builder))
            return cached

        pool = await self._await_singleflight(key, builder)
        if pool is None:
            await asyncio.sleep(0)
            pool = await self._await_singleflight(key, builder)
        if pool is None:
            raise asyncio.TimeoutError("相似帖子候选池暂时无法构建")
        return pool

    async def close(self) -> None:
        """取消尚未完成的后台刷新任务。"""
        async with self._tasks_lock:
            tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _read_cache(self, key: str) -> SimilarThreadCandidatePoolDTO | None:
        """读取并校验 Redis 候选池。"""
        try:
            raw = await self._redis.get(key)
            if not raw:
                return None
            return SimilarThreadCandidatePoolDTO.model_validate_json(raw)
        except Exception:
            logger.warning("读取相似帖子候选池失败: key=%s", key, exc_info=True)
            return None

    async def _write_cache(self, key: str, pool: SimilarThreadCandidatePoolDTO) -> None:
        """写入完整候选池；Redis 故障不影响当前请求。"""
        ttl = (
            self.CACHE_TTL_SECONDS if pool.candidates else self.EMPTY_CACHE_TTL_SECONDS
        )
        try:
            await self._redis.setex(key, ttl, pool.model_dump_json())
        except Exception:
            logger.warning("写入相似帖子候选池失败: key=%s", key, exc_info=True)

    async def _await_singleflight(
        self, key: str, builder: CandidateBuilder
    ) -> SimilarThreadCandidatePoolDTO | None:
        """复用同 Key 正在执行的候选池构建任务。"""
        async with self._tasks_lock:
            task = self._tasks.get(key)
            if task is None:
                task = asyncio.create_task(
                    self._build_and_cleanup(key, builder, background=False)
                )
                self._tasks[key] = task
            else:
                logger.debug("相似帖子候选池 singleflight 命中: key=%s", key)
        return await asyncio.shield(task)

    async def _schedule_soft_refresh(self, key: str, builder: CandidateBuilder) -> None:
        """为软过期 Key 安排一次不排队的后台刷新。"""
        async with self._tasks_lock:
            if key in self._tasks or self._cold_query_semaphore.locked():
                return
            task = asyncio.create_task(
                self._build_and_cleanup(key, builder, background=True)
            )
            self._tasks[key] = task

    async def _build_and_cleanup(
        self,
        key: str,
        builder: CandidateBuilder,
        *,
        background: bool,
    ) -> SimilarThreadCandidatePoolDTO | None:
        """执行受并发限制的候选池构建并清理 singleflight 状态。"""
        acquired = False
        try:
            if background and self._cold_query_semaphore.locked():
                return None
            try:
                await asyncio.wait_for(
                    self._cold_query_semaphore.acquire(),
                    timeout=0.05 if background else self.COLD_QUERY_WAIT_SECONDS,
                )
                acquired = True
            except asyncio.TimeoutError:
                if background:
                    return None
                raise SimilarThreadsBusyError("相似推荐冷查询繁忙")

            candidates, complete = await builder()
            pool = SimilarThreadCandidatePoolDTO(
                generated_at=time.time(), candidates=candidates
            )
            if complete:
                await self._write_cache(key, pool)
            else:
                logger.warning(
                    "相似帖子候选池仅生成部分结果，不写缓存: key=%s count=%s",
                    key,
                    len(candidates),
                )
            return pool
        except asyncio.CancelledError:
            raise
        except Exception:
            if not background:
                raise
            logger.warning("后台刷新相似帖子候选池失败: key=%s", key, exc_info=True)
            return None
        finally:
            if acquired:
                self._cold_query_semaphore.release()
            current_task = asyncio.current_task()
            async with self._tasks_lock:
                if self._tasks.get(key) is current_task:
                    self._tasks.pop(key, None)
