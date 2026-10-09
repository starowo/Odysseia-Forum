"""Watch 日志触发原因。"""

from enum import StrEnum


class RateLimitReason(StrEnum):
    """稳定原因代码及其中文说明。"""

    DAILY_WATCH = "daily_watch"
    GLOBAL_RATE_LIMIT = "global_rate_limit"
    SEARCH_RATE_LIMIT = "search_rate_limit"
    SIMILAR_RATE_LIMIT = "similar_rate_limit"
    ACTIVE_WATCH = "active_watch"

    @property
    def chinese_label(self) -> str:
        """返回适合人工审阅的中文原因。"""
        labels = {
            self.DAILY_WATCH: "每日调用量监控",
            self.GLOBAL_RATE_LIMIT: "全局分钟限流",
            self.SEARCH_RATE_LIMIT: "搜索接口限流",
            self.SIMILAR_RATE_LIMIT: "相似推荐限流",
            self.ACTIVE_WATCH: "持续监控",
        }
        return labels[self]

    @classmethod
    def chinese_label_for(cls, reason: str) -> str:
        """将原因代码转换为中文，未知代码保持原样。"""
        try:
            return cls(reason).chinese_label
        except ValueError:
            return reason
