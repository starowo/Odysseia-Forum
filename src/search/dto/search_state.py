from typing import List, Optional, Set, Dict, Any

from pydantic import BaseModel

from shared.enum.default_preferences import DefaultPreferences


class SearchStateDTO(BaseModel):
    """用于封装 GenericSearchView 所有搜索参数和UI状态的数据传输对象。"""

    channel_ids: List[int] = []

    # 作者偏好
    include_authors: Optional[Set[int]] = None
    exclude_authors: Optional[Set[int]] = None

    # 标签偏好
    include_tags: Set[str] = set()
    exclude_tags: Set[str] = set()
    all_available_tags: List[str] = []  # 所有可供选择的标签，用于UI展示

    # 关键词偏好
    keywords: str = ""
    exclude_keywords: str = ""
    exemption_markers: List[str] = ["禁", "🈲"]

    # 排序和逻辑
    tag_logic: str = "or"  # "or" 或 "and"
    sort_method: str = "comprehensive"
    sort_order: str = "desc"  # "asc" 或 "desc"

    # 基础排序算法（在自定义筛选后应用）
    custom_base_sort: str = "comprehensive"
    # 数值范围 (使用数学区间表示法)
    reaction_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    reply_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    # 时间范围
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    active_after: Optional[str] = None
    active_before: Optional[str] = None

    # 显示偏好
    preview_image_mode: str = DefaultPreferences.PREVIEW_IMAGE_MODE.value
    results_per_page: int = DefaultPreferences.RESULTS_PER_PAGE.value

    # UI 状态
    page: int = 0
    tag_page: int = 0

    # 策略信息 (用于超时恢复)
    strategy_type: str = "default"
    strategy_params: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True  # 允许Set类型
        from_attributes = True  # 允许从ORM模型创建
