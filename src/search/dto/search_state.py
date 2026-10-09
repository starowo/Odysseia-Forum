from typing import List, Optional, Set

from pydantic import BaseModel, ConfigDict

from shared.enum import DefaultPreferences


class SearchStateDTO(BaseModel):
    """用于封装 GenericSearchView 所有搜索参数和UI状态的数据传输对象。"""

    channel_ids: List[int] = []
    """所选频道 ID 列表"""

    include_authors: Optional[Set[int]] = None
    """必须包含的作者 ID 集合"""

    exclude_authors: Optional[Set[int]] = None
    """必须排除的作者 ID 集合"""

    include_tags: Set[str] = set()
    """正选标签名称集合"""

    exclude_tags: Set[str] = set()
    """反选标签名称集合"""

    all_available_tags: List[str] = []
    """所有可供选择的标签列表，虚拟标签固定排在最前"""

    virtual_tags: List[str] = []
    """所选频道映射生成的虚拟标签列表"""

    can_view_abyss_tags: bool = False
    """当前交互用户是否可在候选列表中看到深渊向 TAG"""

    keywords: str = ""
    """搜索包含的关键词文本"""

    exclude_keywords: str = ""
    """搜索排除的关键词文本"""

    exemption_markers: List[str] = ["禁", "🈲"]
    """排除关键词的豁免标记列表"""

    tag_logic: str = "or"
    """多正选标签的匹配逻辑，可选 'or' 或 'and'"""

    sort_method: str = "comprehensive"
    """搜索结果的排序方法"""

    sort_order: str = "desc"
    """排序的顺序，可选 'asc' 或 'desc'"""

    custom_base_sort: str = "comprehensive"
    """自定义筛选时的基础排序算法"""

    reaction_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    """反应数筛选的数学区间范围"""

    reply_count_range: str = DefaultPreferences.DEFAULT_NUMERIC_RANGE.value
    """回复数筛选的数学区间范围"""

    created_after: Optional[str] = None
    """帖子发帖时间下限"""

    created_before: Optional[str] = None
    """帖子发帖时间上限"""

    active_after: Optional[str] = None
    """帖子最后活跃时间下限"""

    active_before: Optional[str] = None
    """帖子最后活跃时间上限"""

    preview_image_mode: str = DefaultPreferences.PREVIEW_IMAGE_MODE.value
    """预览图显示模式"""

    results_per_page: int = DefaultPreferences.RESULTS_PER_PAGE.value
    """每页显示的搜索结果数量"""

    page: int = 0
    """当前搜索结果的分页页码"""

    tag_page: int = 0
    """当前标签选择界面的分页页码"""

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)
