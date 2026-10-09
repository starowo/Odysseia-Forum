from typing import List, Optional

from sqlmodel import JSON, BigInteger, Column, Field, SQLModel, UniqueConstraint


class UserSearchPreferences(SQLModel, table=True):
    """用户搜索偏好模型"""

    __tablename__ = "user_search_preferences"  # type: ignore[assignment]

    __table_args__ = (
        UniqueConstraint("user_id", "guild_id", name="uk_user_guild_preferences"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    """主键ID"""

    user_id: int = Field(sa_column=Column(BigInteger, index=True, nullable=False))
    """用户ID"""

    guild_id: int = Field(
        default=0,
        sa_column=Column(BigInteger, index=True, nullable=False),
        description="用户偏好所属的服务器 ID",
    )
    """服务器ID"""

    # 频道选择
    preferred_channels: Optional[List[int]] = Field(
        default=None, sa_column=Column(JSON)
    )
    """偏好的频道ID列表"""

    # 作者偏好
    include_authors: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))
    """包含的作者ID列表"""

    exclude_authors: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))
    """排除的作者ID列表"""

    # 时间偏好
    created_after: Optional[str] = Field(default=None)
    """创建时间晚于"""

    created_before: Optional[str] = Field(default=None)
    """创建时间早于"""

    active_after: Optional[str] = Field(default=None)
    """活跃时间晚于"""

    active_before: Optional[str] = Field(default=None)
    """活跃时间早于"""

    # 标签偏好
    include_tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    """包含的标签列表"""

    exclude_tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    """排除的标签列表"""

    # 关键词偏好
    include_keywords: str = Field(default="")
    """包含的关键词"""

    exclude_keywords: str = Field(default="")
    """排除的关键词"""

    exclude_keyword_exemption_markers: List[str] = Field(
        default=["禁", "🈲"], sa_column=Column(JSON)
    )
    """关键词排除豁免标记"""

    # 显示偏好
    preview_image_mode: str = Field(default="thumbnail")
    """预览图片模式"""

    results_per_page: int = Field(default=5)
    """每页结果数量"""

    ui_page_size: int = Field(default=48)
    """网页端每页结果数量"""

    # 排序算法偏好
    sort_method: str = Field(default="comprehensive", nullable=False)
    """排序方法"""

    custom_base_sort: str = Field(default="comprehensive", nullable=False)
    """自定义排序的基础算法"""
