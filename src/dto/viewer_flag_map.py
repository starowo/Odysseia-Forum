from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ViewerFlagMap:
    """保存一批作品的查看者关系标记。"""

    values: dict[int, set[str]]

    def for_thread(self, thread_id: int) -> list[str]:
        """按稳定顺序返回指定作品的关系标记。"""
        order = ("collected", "followed", "followed_author", "unread")
        flags = self.values.get(thread_id, set())
        return [flag for flag in order if flag in flags]
