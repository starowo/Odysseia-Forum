from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class UserSearchPreferencesDTO(BaseModel):
    """用于传输用户搜索偏好设置的数据传输对象。"""

    user_id: int
    """用户ID"""

    preferred_channels: Optional[List[int]] = None
    """偏好的频道ID列表"""

    # 作者偏好
    include_authors: Optional[List[int]] = None
    """包含的作者ID列表"""

    exclude_authors: Optional[List[int]] = None
    """排除的作者ID列表"""

    # 标签偏好
    include_tags: Optional[List[str]] = None
    """包含的标签列表 (名称)"""

    exclude_tags: Optional[List[str]] = None
    """排除的标签列表 (名称)"""

    # 关键词偏好
    include_keywords: str = ""
    """包含的关键词"""

    exclude_keywords: str = ""
    """排除的关键词"""

    exclude_keyword_exemption_markers: List[str] = ["禁", "🈲"]
    """关键词排除豁免标记（包含这些标记的帖子即使匹配排除关键词也不会被过滤）"""

    # 时间偏好
    created_after: Optional[str] = None
    """创建时间晚于（ISO 8601 格式）"""

    created_before: Optional[str] = None
    """创建时间早于（ISO 8601 格式）"""

    active_after: Optional[str] = None
    """最后活跃时间晚于（ISO 8601 格式）"""

    active_before: Optional[str] = None
    """最后活跃时间早于（ISO 8601 格式）"""

    # 显示偏好
    preview_image_mode: str = "thumbnail"
    """预览图片模式（thumbnail/full）"""

    results_per_page: int = 5
    """每页结果数量"""

    ui_page_size: int = 48
    """网页端每页结果数量"""

    # 排序算法偏好
    sort_method: str = "comprehensive"
    """排序方法（comprehensive/created/active/custom）"""

    custom_base_sort: str = "comprehensive"
    """自定义排序时使用的基础排序算法"""

    model_config = ConfigDict(from_attributes=True)
