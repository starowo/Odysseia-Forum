from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class Booklist(SQLModel, table=True):
    """书单元数据"""

    __tablename__ = "booklist"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)

    # 创建者 ID
    owner_id: int = Field(index=True, description="创建该书单的用户Discord ID")

    title: str = Field(index=True, description="书单标题")
    description: Optional[str] = Field(default=None, description="书单简介")

    # 封面图，可以是书单内第一个帖子的图，也可以是自定义
    cover_image_url: Optional[str] = Field(default=None, description="书单封面")

    # 状态字段
    is_public: bool = Field(default=True, index=True, description="是否公开")
    display_type: int = Field(
        default=1, description="展示方式: 1-加入时间倒序, 2-display_order"
    )

    # 统计数据
    item_count: int = Field(default=0, description="书单内帖子数量")
    view_count: int = Field(default=0, description="被浏览次数")
    collection_count: int = Field(default=0, description="被收藏次数")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        description="最后更新时间",
    )
