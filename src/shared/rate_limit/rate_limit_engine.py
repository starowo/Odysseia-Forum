"""基于 Redis 的固定窗口频率限制器 + watch 标记。

使用 INCR + EXPIRE 实现，每个用户独立计数，窗口到期后自动重置。
"""

import logging
import math
import time
from datetime import datetime, time as datetime_time, timedelta

from redis.asyncio import Redis

from dto.rate_limit import (
    GlobalRateLimitConfig,
    GlobalRateLimitResult,
    RateLimitResult,
)
from shared.enum.cache_keys import CacheKeys
from shared.enum.rate_limit_defaults import RateLimitDefaults

logger = logging.getLogger(__name__)

_GLOBAL_RATE_LIMIT_SCRIPT = """
local minute_count = redis.call('INCR', KEYS[1])
local minute_ttl = redis.call('TTL', KEYS[1])
if minute_count == 1 or minute_ttl < 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    minute_ttl = tonumber(ARGV[1])
end

local daily_count = redis.call('INCR', KEYS[2])
local daily_ttl = redis.call('TTL', KEYS[2])
if daily_count == 1 or daily_ttl < 1 then
    redis.call('EXPIRE', KEYS[2], ARGV[2])
end

local minute_limited = minute_count > tonumber(ARGV[3])
local daily_watch_active = daily_count > tonumber(ARGV[4])
local watched = redis.call('EXISTS', KEYS[3]) == 1

if minute_limited or daily_watch_active then
    redis.call('SET', KEYS[3], '1', 'EX', ARGV[5])
    watched = true
end

return {
    minute_count,
    minute_ttl,
    daily_count,
    watched and 1 or 0,
    daily_watch_active and 1 or 0
}
"""


async def check_rate_limit(
    redis: Redis,
    key: str,
    max_requests: int = 40,
    window_seconds: int = 60,
) -> RateLimitResult:
    """检查是否超出频率限制（固定窗口算法）。

    每次请求对 Redis key 执行 INCR。
    首次请求（INCR 返回 1）时设置 EXPIRE，窗口到期后 key 自动删除、计数归零。

    Args:
        redis: Redis 客户端。
        key: 限流的 Redis key（如 ``rate_limit:search:123``）。
        max_requests: 窗口内允许的最大请求数。
        window_seconds: 窗口时长（秒）。

    Returns:
        RateLimitResult: 包含是否允许、剩余次数、重置倒计时。
    """
    try:
        # 确保类型为纯 int（调用方可能传入 IntEnum，redis-py 部分版本不兼容）
        max_requests = int(max_requests)
        window_seconds = int(window_seconds)

        current = await redis.incr(key)

        if current == 1:
            # 首次请求，设置过期时间
            await redis.expire(key, window_seconds)
            ttl = window_seconds
        else:
            ttl = await redis.ttl(key)
            if ttl <= 0:
                # key 已存在但 TTL 丢失（极端情况），补设
                await redis.expire(key, window_seconds)
                ttl = window_seconds

        remaining = max(0, max_requests - current)

        return RateLimitResult(
            allowed=current <= max_requests,
            current_count=current,
            remaining=remaining,
            reset_after=ttl,
        )
    except Exception:
        logger.warning("Redis 频率限制检查失败，降级放行", exc_info=True)
        return RateLimitResult.fail_open()


async def check_global_rate_limit(
    redis: Redis,
    user_id: str,
    config: GlobalRateLimitConfig,
    now_timestamp: float | None = None,
) -> GlobalRateLimitResult:
    """原子检查全局分钟限制、每日计数和 Watch 状态。"""
    date_key, daily_ttl = _get_local_day_window(now_timestamp)
    minute_key = CacheKeys.RATE_LIMIT_GLOBAL_MINUTE.format(user_id=user_id)
    daily_key = CacheKeys.RATE_LIMIT_GLOBAL_DAILY.format(date=date_key, user_id=user_id)
    watch_key = CacheKeys.RATE_LIMIT_WATCH.format(user_id=user_id)

    try:
        # 单次 Redis 调用同时维护所有全局频率状态
        raw_result = await redis.eval(
            _GLOBAL_RATE_LIMIT_SCRIPT,
            3,
            minute_key,
            daily_key,
            watch_key,
            config.window_seconds,
            daily_ttl,
            config.max_requests,
            config.daily_watch_threshold,
            int(RateLimitDefaults.WATCH_TTL_SECONDS),
        )
        minute_count = int(raw_result[0])
        reset_after = int(raw_result[1])
        daily_count = int(raw_result[2])
        return GlobalRateLimitResult(
            allowed=minute_count <= config.max_requests,
            minute_count=minute_count,
            minute_remaining=max(0, config.max_requests - minute_count),
            reset_after=reset_after,
            daily_count=daily_count,
            watched=bool(raw_result[3]),
            daily_watch_active=bool(raw_result[4]),
        )
    except Exception:
        logger.warning("Redis 全局频率限制检查失败，降级放行", exc_info=True)
        return GlobalRateLimitResult.fail_open(config.max_requests)


def _get_local_day_window(now_timestamp: float | None = None) -> tuple[str, int]:
    """返回服务器本地日期键及距次日零点的秒数。"""
    current_timestamp = time.time() if now_timestamp is None else now_timestamp
    local_now = datetime.fromtimestamp(current_timestamp)
    next_date = local_now.date() + timedelta(days=1)
    next_midnight = datetime.combine(next_date, datetime_time.min)
    next_midnight_timestamp = time.mktime(next_midnight.timetuple())
    ttl_seconds = max(1, math.ceil(next_midnight_timestamp - current_timestamp))
    return local_now.strftime("%Y%m%d"), ttl_seconds


async def set_rate_limit_watch(redis: Redis, user_id: str) -> None:
    """为指定用户设置 watch 标记，TTL 内所有请求将被详细记录。

    Args:
        redis: Redis 客户端。
        user_id: 要标记的用户 ID。
    """
    try:
        key = CacheKeys.RATE_LIMIT_WATCH.format(user_id=user_id)
        await redis.setex(key, int(RateLimitDefaults.WATCH_TTL_SECONDS), "1")
    except Exception:
        logger.warning("设置 watch 标记失败: user_id=%s", user_id, exc_info=True)


async def is_user_watched(redis: Redis, user_id: str) -> bool:
    """检查用户当前是否处于 watch 状态。

    Args:
        redis: Redis 客户端。
        user_id: 要检查的用户 ID。

    Returns:
        True 表示该用户的 watch 标记存在且未过期，
        False 表示不存在或 Redis 不可用。
    """
    try:
        key = CacheKeys.RATE_LIMIT_WATCH.format(user_id=user_id)
        return await redis.get(key) is not None
    except Exception:
        return False
