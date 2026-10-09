from dataclasses import dataclass


@dataclass
class CategoryMeta:
    """分类元数据，用于替代 discord.CategoryChannel 的属性读取"""

    id: int
    name: str
