from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from api.v1.schemas.search.author_detail import AuthorDetail
from dto.custom_tag_binding_response import CustomTagBindingResponse
from shared.utc_datetime import UTCDateTime


class BooklistSummary(BaseModel):
    """书单摘要（列表用）"""

    id: int = Field(description="书单ID")
    """书单ID"""

    owner_id: int = Field(description="创建者用户ID")
    """创建者用户ID"""

    title: str = Field(description="书单标题")
    """书单标题"""

    custom_tags: list[CustomTagBindingResponse] = Field(
        default_factory=list,
        description="书单自身当前生效的本地绑定标签列表（可包含 DC 标签实体），包含内部 ID、标准名、分类、绑定轮次及正负票数",
    )
    """书单自身当前生效的自定义标签及票数，不继承单内帖子的标签"""

    description: Optional[str] = Field(None, description="书单简介")
    """书单简介"""

    cover_image_url: Optional[str] = Field(None, description="书单封面图URL")
    """书单封面图URL"""

    author: Optional[AuthorDetail] = Field(None, description="创建者信息")
    """创建者信息"""

    is_public: bool = Field(description="是否公开")
    """是否公开"""

    is_anonymous: bool = Field(description="是否匿名")
    """是否匿名"""

    is_default: bool = Field(description="是否为用户的默认书单")
    """是否为用户的默认书单"""

    is_tournament: bool = Field(False, description="是否为赛事书单")
    """是否为赛事书单"""

    tournament_channel_id: Optional[int] = Field(None, description="赛事频道ID")
    """赛事频道ID"""

    default_sort_method: str = Field(
        default="join_time",
        description="默认排序方式: hot, created_at, reaction_count, reply_count, collection_count, last_active_at, join_time, display_order",
    )
    """默认排序方式"""

    default_sort_order: str = Field(
        default="desc", description="默认排序顺序: asc, desc"
    )
    """默认排序顺序"""

    item_count: int = Field(description="书单内帖子数量")
    """书单内帖子数量"""

    collection_count: int = Field(description="被收藏次数")
    """被收藏次数"""

    view_count: int = Field(description="被浏览次数")
    """被浏览次数"""

    publish_status: int = Field(
        default=0, description="发布状态: 0-未发布 1-待处理 2-成功 3-失败"
    )
    """发布状态: 0-未发布 1-待处理 2-成功 3-失败"""

    created_at: UTCDateTime = Field(description="创建时间")
    """创建时间"""

    updated_at: UTCDateTime = Field(description="最后更新时间")
    """最后更新时间"""

    collected_flag: bool = Field(False, description="当前用户是否收藏了该书单")
    """当前用户是否收藏了该书单"""

    is_marked: bool = Field(
        False,
        description="是否被标记帖子命中 (仅当请求传入mark_thread_id时有效)",
    )
    """是否被标记帖子命中"""

    @field_serializer("owner_id")
    def serialize_owner_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)

    @field_serializer("tournament_channel_id")
    def serialize_tournament_channel_id(self, value: int | None) -> str | None:
        """将 Discord 频道 ID 序列化为字符串，避免 JavaScript 精度丢失"""
        if value is None:
            return None
        return str(value)

    model_config = ConfigDict(from_attributes=True)
