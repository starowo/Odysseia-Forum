from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndexUpdatedEvent:
    """表示索引内容发生变化且核心缓存需要刷新。"""
