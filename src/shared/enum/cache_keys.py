from enum import StrEnum


class CacheKeys(StrEnum):
    """Redis 缓存 Key 常量"""

    USER_PREFERENCES = "user_prefs:{user_id}:{guild_id}"
    """用户搜索偏好缓存"""

    FTS_TSQUERY_RESULT = "fts:tsquery:result:{prefix}:{hash}"
    """FTS tsquery 分词结果缓存（避免重复 jieba 分词）"""

    TOURNAMENT_THREAD = "tournament:thread:{thread_id}"
    """帖子赛事信息缓存"""

    SIMILAR_CANDIDATES_STANDARD = "similar:candidates:standard:{thread_id}"
    """不含深渊区的相似帖子候选池"""

    SIMILAR_CANDIDATES_ABYSS = "similar:candidates:abyss:{thread_id}"
    """允许包含深渊区的相似帖子候选池"""

    RATE_LIMIT_WATCH = "rate_limit:watch:{user_id}"
    """限流触发后的 watch 标记"""

    RATE_LIMIT_GLOBAL_MINUTE = "rate_limit:global:{user_id}"
    """全局分钟固定窗口计数"""

    RATE_LIMIT_GLOBAL_DAILY = "rate_limit:global:daily:{date}:{user_id}"
    """服务器本地自然日全局请求计数"""

    def format(self, **kwargs) -> str:
        """填充 Key 中的占位符。"""
        return self.value.format(**kwargs)
