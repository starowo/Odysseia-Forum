from dataclasses import dataclass
from datetime import datetime

from dto.author_dto import AuthorDTO
from dto.thread_dto import ThreadDTO


@dataclass(frozen=True, slots=True)
class FollowedThreadRecordDTO:
    """传递关注列表中的作品与关注关系数据。"""

    thread: ThreadDTO
    author: AuthorDTO | None
    followed_at: datetime
    last_viewed_at: datetime | None
    active_flag: bool

    @property
    def thread_id(self) -> int:
        """兼容旧仓库调用方返回作品 Discord ID。"""
        return self.thread.thread_id

    @property
    def title(self) -> str:
        """兼容旧仓库调用方返回作品标题。"""
        return self.thread.title

    @property
    def has_update(self) -> bool:
        """保留旧时间投影推导值，API 已改用动态通知未读状态。"""
        latest = self.thread.latest_update_at
        return latest is not None and (
            self.last_viewed_at is None or latest > self.last_viewed_at
        )
