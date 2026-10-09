from dataclasses import dataclass


@dataclass
class GuildMeta:
    """服务器元数据，用于替代 discord.Guild 的属性读取"""

    id: int
    name: str
