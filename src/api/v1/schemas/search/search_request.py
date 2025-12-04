from pydantic import BaseModel, Field
from typing import Optional, List
from src.shared.enum.default_preferences import DefaultPreferences


class SearchRequest(BaseModel):
    """
    帖子搜索的 API 请求模型

    包含所有可用的搜索条件,用于精确查找论坛帖子
    """

    channel_ids: Optional[List[str]] = Field(
        default=None, description="要搜索的频道ID列表(字符串格式,避免精度损失),为空则搜索所有频道"
    )
    include_tags: List[str] = Field(
        default_factory=list, description="必须包含的标签名列表"
    )
    exclude_tags: List[str] = Field(
        default_factory=list, description="必须排除的标签名列表"
    )
    tag_logic: str = Field(
        default="and",
        description="多标签搜索逻辑: 'and'(所有标签都匹配), 'or'(任意标签匹配)",
    )
    keywords: Optional[str] = Field(
        default=None, description="搜索关键词，使用逗号分隔 AND 逻辑，斜杠分隔 OR 逻辑"
    )
    exclude_keywords: Optional[str] = Field(
        default=None, description="要排除的关键词，使用逗号分隔"
    )
    exclude_keyword_exemption_markers: Optional[List[str]] = Field(
        default=None,
        description="关键词排除的豁免标记，附近包含这些标记的反选关键词不会被排除",
    )
    include_authors: Optional[List[int]] = Field(
        default=None, description="只看这些作者的帖子，作者ID列表"
    )
    exclude_authors: Optional[List[int]] = Field(
        default=None, description="屏蔽这些作者的帖子，作者ID列表"
    )
    author_name: Optional[str] = Field(
        default=None, description="模糊搜索作者的全局用户名或昵称"
    )
    created_after: Optional[str] = Field(
        default=None,
        description="发帖时间晚于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    created_before: Optional[str] = Field(
        default=None,
        description="发帖时间早于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    active_after: Optional[str] = Field(
        default=None,
        description="最后活跃时间晚于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    active_before: Optional[str] = Field(
        default=None,
        description="最后活跃时间早于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    reaction_count_range: str = Field(
        default=DefaultPreferences.DEFAULT_NUMERIC_RANGE.value,
        description="点赞数范围 (例如: '>10', '5-20')",
    )
    reply_count_range: str = Field(
        default=DefaultPreferences.DEFAULT_NUMERIC_RANGE.value,
        description="回复数范围 (例如: '>=5')",
    )
    sort_method: str = Field(
        default="comprehensive",
        description="排序方法：'comprehensive'(综合排序), "
        "'created_at'(发帖时间), 'last_active'(最后活跃时间), "
        "'reaction_count'(点赞数), 'reply_count'(回复数), "
        "'custom'(自定义)",
    )
    custom_base_sort: str = Field(
        default="comprehensive",
        description="当排序方法为 'custom' 时，作为基础的排序算法",
    )
    sort_order: str = Field(
        default="desc", description="排序顺序：'asc'(升序) 或 'desc'(降序)"
    )
    limit: int = Field(
        default=10, ge=1, le=100, description="每次请求期望返回的新帖子数量 (范围: 1-100)"
    )
    exclude_thread_ids: List[int] = Field(
        default_factory=list,
        description="已在前端展示的帖子 thread_id 列表，本次请求将排除这些帖子"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="结果的偏移页（已弃用，为兼容旧版本保留）"
    )
