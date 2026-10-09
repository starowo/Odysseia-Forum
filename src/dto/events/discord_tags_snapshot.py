from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DiscordTagsSnapshot:
    """成功读取的完整论坛标签快照，失败和权限丢失不发布。"""

    channel_id: int
    """Discord 来源频道 ID"""
    tags: dict[int, str]
    """完整可用标签 ID 到名称的映射，空集合也有效"""
    observed_at: datetime
    """开始读取快照时的 UTC 时间，防止过期响应覆盖新状态"""
