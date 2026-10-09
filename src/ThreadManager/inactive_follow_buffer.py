"""Redis 缓冲层：将待标记为非活跃的关注暂存到 Redis Set，定时批量写入 DB。"""

import asyncio
import logging
from typing import List

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.follow_repository import ThreadFollowRepository
from shared.redis_client import RedisManager

logger = logging.getLogger(__name__)

# Redis key 前缀与 TTL
INACTIVE_PENDING_PREFIX = "inactive:pending"
INACTIVE_PENDING_TTL = 600  # 10 分钟，防止僵尸 key


class InactiveFollowBuffer:
    """将 on_thread_member_remove 事件缓冲到 Redis Set，定时批量 UPDATE DB。"""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        interval: int = 30,
    ):
        self.session_factory = session_factory
        self.interval = interval
        self._task: asyncio.Task | None = None
        logger.debug("InactiveFollowBuffer 已初始化，间隔=%ds", interval)

    # ---------------------------------------------------------------
    # 公共方法
    # ---------------------------------------------------------------

    async def add(self, thread_id: int, user_id: int) -> None:
        """将一个 (thread_id, user_id) 写入 Redis 待处理集合。"""
        try:
            redis = RedisManager.get_client()
            key = f"{INACTIVE_PENDING_PREFIX}:{thread_id}"
            await redis.sadd(key, str(user_id))
            await redis.expire(key, INACTIVE_PENDING_TTL)
        except Exception:
            logger.error(
                f"Redis SADD 失败: thread={thread_id} user={user_id}", exc_info=True
            )

    def start(self) -> None:
        """启动后台定时 flush 任务。"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
            logger.debug("InactiveFollowBuffer 后台任务已启动，间隔=%ds", self.interval)

    async def stop(self) -> None:
        """停止后台任务并执行最后一次 flush。"""
        if self._task and not self._task.done():
            self._task.cancel()
        logger.debug("InactiveFollowBuffer 正在执行最后 flush...")
        await self.flush_all()
        logger.debug("InactiveFollowBuffer 最后 flush 完成。")

    # ---------------------------------------------------------------
    # 内部方法
    # ---------------------------------------------------------------

    async def flush_all(self) -> int:
        """
        扫描 Redis 中所有待处理 key，逐线程批量写入 DB。
        返回总共标记为非活跃的记录数。
        """
        total = 0
        try:
            redis = RedisManager.get_client()
            pattern = f"{INACTIVE_PENDING_PREFIX}:*"

            # 使用 SCAN 而非 KEYS，避免阻塞 Redis
            cursor = 0
            keys: List[str] = []
            while True:
                cursor, batch = await redis.scan(cursor, match=pattern, count=100)
                keys.extend(batch)
                if cursor == 0:
                    break

            if not keys:
                return 0

            async with self.session_factory() as session:
                repo = ThreadFollowRepository(session)
                for key in keys:
                    try:
                        # 解析 thread_id
                        thread_id_str = key.split(":")[-1]
                        thread_id = int(thread_id_str)

                        # 读取全部成员 ID
                        members_raw = await redis.smembers(key)
                        user_ids = [int(uid) for uid in members_raw]

                        if user_ids:
                            count = await repo.batch_mark_inactive(
                                thread_id=thread_id, user_ids=user_ids
                            )
                            total += count

                        # 删除已处理的 key
                        await redis.delete(key)

                    except Exception:
                        logger.error(
                            f"flush 处理 key={key} 时出错，跳过", exc_info=True
                        )

            if total:
                logger.debug(
                    f"InactiveFollowBuffer flush 完成，共标记 {total} 条为非活跃"
                )
        except Exception:
            logger.error("InactiveFollowBuffer flush_all 失败", exc_info=True)

        return total

    async def _run_loop(self) -> None:
        """后台定时循环。"""
        while True:
            try:
                await asyncio.sleep(self.interval)
                await self.flush_all()
            except asyncio.CancelledError:
                logger.info("InactiveFollowBuffer 后台任务已取消。")
                break
            except Exception:
                logger.error("InactiveFollowBuffer 后台循环异常", exc_info=True)
