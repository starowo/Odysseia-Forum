from typing import Optional, List
from sqlmodel import Field, SQLModel, JSON, Column
from datetime import datetime


class UserSearchPreferences(SQLModel, table=True):
    """用户搜索偏好模型"""

    user_id: int = Field(primary_key=True)

    # 频道选择
    preferred_channels: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))

    # 作者偏好
    include_authors: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))
    exclude_authors: Optional[List[int]] = Field(default=None, sa_column=Column(JSON))

    # 时间偏好
    after_date: Optional[datetime] = Field(default=None)
    before_date: Optional[datetime] = Field(default=None)

    # 标签偏好
    include_tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    exclude_tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    # 关键词偏好
    include_keywords: str = Field(default="")
    exclude_keywords: str = Field(default="")
    exclude_keyword_exemption_markers: List[str] = Field(
        default=["禁", "🈲"], sa_column=Column(JSON)
    )

    # 显示偏好
    preview_image_mode: str = Field(default="thumbnail")
    results_per_page: int = Field(default=5)
