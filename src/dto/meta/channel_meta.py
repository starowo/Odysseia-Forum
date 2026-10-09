from dataclasses import dataclass, field

from dto.meta.category_meta import CategoryMeta
from dto.meta.guild_meta import GuildMeta
from dto.meta.tag_meta import TagMeta


@dataclass
class ChannelMeta:
    """频道元数据，用于替代 discord.ForumChannel 的属性读取"""

    id: int
    name: str
    guild: GuildMeta
    category_id: int | None = None
    category: CategoryMeta | None = None
    available_tags: list[TagMeta] = field(default_factory=list)
