from dataclasses import dataclass


@dataclass
class TagMeta:
    """标签元数据，用于替代 discord.ForumTag 的属性读取"""

    id: int
    name: str
