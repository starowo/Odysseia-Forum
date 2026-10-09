from typing import List, Optional, Union, Any

from pydantic import BaseModel, Field, field_validator


class UserPreferencesUpdateRequest(BaseModel):
    """用于更新用户搜索偏好设置的 API 请求模型"""

    # 频道选择
    preferred_channels: Optional[List[Union[int, str]]] = Field(
        default=None,
        description="用户偏好的频道ID列表，搜索时优先在这些频道中查找，支持数字或字符串",
    )
    """偏好的频道ID列表"""

    # 作者偏好
    include_authors: Optional[List[Union[int, str]]] = Field(
        default=None, description="只看这些作者的帖子，作者ID列表，支持数字或字符串"
    )
    """包含的作者ID列表"""

    exclude_authors: Optional[List[Union[int, str]]] = Field(
        default=None, description="屏蔽这些作者的帖子，作者ID列表，支持数字或字符串"
    )
    """排除的作者ID列表"""

    # 标签偏好
    include_tags: Optional[List[str]] = Field(
        default=None, description="必须包含的标签名列表"
    )
    """包含的标签列表"""

    exclude_tags: Optional[List[str]] = Field(
        default=None, description="必须排除的标签名列表"
    )
    """排除的标签列表"""

    # 关键词偏好
    include_keywords: Optional[str] = Field(
        default=None, description="搜索关键词，使用逗号分隔 AND 逻辑，斜杠分隔 OR 逻辑"
    )
    """包含的关键词"""

    exclude_keywords: Optional[str] = Field(
        default=None, description="要排除的关键词，使用逗号分隔"
    )
    """排除的关键词"""

    exclude_keyword_exemption_markers: Optional[List[str]] = Field(
        default=None,
        description="关键词排除的豁免标记列表，包含这些标记的关键词不会被排除",
    )
    """关键词排除豁免标记"""

    # 显示偏好
    preview_image_mode: Optional[str] = Field(
        default=None,
        description="预览图片显示模式：'thumbnail'(缩略图), "
        "'full'(完整图), 'none'(不显示)",
    )
    """预览图片模式"""

    results_per_page: Optional[int] = Field(
        default=None, description="每页显示的结果数量，必须小于10"
    )
    """每页结果数量"""

    ui_page_size: Optional[int] = Field(
        default=None, description="网页端每页显示的结果数量"
    )
    """网页端每页结果数量"""

    # 排序算法偏好
    sort_method: Optional[str] = Field(
        default=None,
        description="排序方法：'comprehensive'(综合排序), "
        "'created_at'(发帖时间), 'last_active'(最后活跃时间), "
        "'reaction_count'(点赞数), 'reply_count'(回复数), 'collection_count'(收藏数)",
    )
    """排序方法"""

    custom_base_sort: Optional[str] = Field(
        default=None, description="自定义排序的基础算法，用于自定义排序时作为基础"
    )
    """自定义排序的基础算法"""

    # 时间偏好
    created_after: Optional[str] = Field(
        default=None,
        description="发帖时间晚于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    """创建时间晚于"""

    created_before: Optional[str] = Field(
        default=None,
        description="发帖时间早于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    """创建时间早于"""

    active_after: Optional[str] = Field(
        default=None,
        description="最后活跃时间晚于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    """活跃时间晚于"""

    active_before: Optional[str] = Field(
        default=None,
        description="最后活跃时间早于此日期 (格式: YYYY-MM-DD 或相对时间如 -7d)",
    )
    """活跃时间早于"""

    @field_validator("results_per_page")
    @classmethod
    def validate_results_per_page(cls, v: Optional[int]) -> Optional[int]:
        """
        验证每页结果数量必须小于10
        """
        if v is not None and v >= 10:
            raise ValueError("Discord BOT 搜索每页结果数量必须小于10")
        return v

    @field_validator("ui_page_size")
    @classmethod
    def validate_ui_page_size(cls, v: Optional[int]) -> Optional[int]:
        """
        验证网页端每页结果数量必须小于101
        """
        if v is not None and v >= 101:
            raise ValueError("网页端每页结果数量不能大于100")
        return v

    @field_validator(
        "preferred_channels", "include_authors", "exclude_authors", mode="before"
    )
    @classmethod
    def convert_ids_to_int(cls, v: Any) -> Any:
        """
        在 Pydantic 校验前，将字符串形式的 Discord ID 转换为 int。
        """
        if v is None:
            return v

        if isinstance(v, list):
            processed = []
            for item in v:
                if isinstance(item, str) and item.isdigit():
                    processed.append(int(item))
                else:
                    processed.append(item)
            return processed

        return v
