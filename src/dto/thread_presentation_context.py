from dataclasses import dataclass, field

from dto.thread_update_dto import ThreadUpdateDTO
from dto.custom_tag_binding_response import CustomTagBindingResponse
from dto.viewer_flag_map import ViewerFlagMap


@dataclass(frozen=True, slots=True)
class ThreadPresentationContext:
    """保存批量构建作品响应所需的附加数据。"""

    viewer_flags: ViewerFlagMap
    """按帖子组织的查看者收藏、关注及未读等状态"""

    latest_updates: dict[int, ThreadUpdateDTO]
    """以 Discord 帖子 ID 为键的最新作品更新信息"""

    custom_tags: dict[int, list[CustomTagBindingResponse]] = field(default_factory=dict)
    """以内部帖子 ID 为键的当前本地标签列表，包含分类、绑定轮次及正负票数"""

    native_tag_ids: dict[int, set[int]] = field(default_factory=dict)
    """按内部帖子 ID 保存当前只读绑定的标准标签 ID，不根据概念来源推断"""
