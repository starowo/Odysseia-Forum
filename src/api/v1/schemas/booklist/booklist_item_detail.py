from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from api.v1.schemas.search.author_detail import AuthorDetail
from api.v1.schemas.search.latest_update import LatestUpdate
from api.v1.schemas.search.thread_detail import ViewerFlag
from shared.utc_datetime import UTCDateTime


class BooklistItemDetail(BaseModel):
    """书单项目详情，包含帖子信息"""

    booklist_item_id: int = Field(description="书单项ID")
    """书单项ID"""

    thread_id: int = Field(description="帖子ID")
    """帖子ID"""

    guild_id: int = Field(default=0, description="帖子所属的 Discord 服务器 ID")
    """帖子所属的 Discord 服务器 ID"""

    channel_id: int = Field(description="频道ID")
    """频道ID"""

    title: str = Field(description="帖子标题")
    """帖子标题"""

    author: AuthorDetail = Field(description="帖子作者信息")
    """帖子作者信息"""

    created_at: UTCDateTime = Field(description="帖子创建时间")
    """帖子创建时间"""

    last_active_at: Optional[UTCDateTime] = Field(
        default=None, description="帖子最后活跃时间"
    )
    """帖子最后活跃时间"""

    reaction_count: int = Field(description="帖子点赞数")
    """帖子点赞数"""

    reply_count: int = Field(description="帖子回复数")
    """帖子回复数"""

    display_count: int = Field(default=0, description="在搜索结果中的展示次数")
    """在搜索结果中的展示次数"""

    first_message_excerpt: Optional[str] = Field(
        default=None, description="帖子首条消息摘要"
    )
    """帖子首条消息摘要"""

    latest_update_at: Optional[UTCDateTime] = Field(
        default=None, description="最新更新时间"
    )
    """最新更新时间"""

    latest_update_link: Optional[str] = Field(
        default=None, description="最新版消息链接"
    )
    """最新版消息链接"""

    collection_count: int = Field(default=0, description="帖子被收藏的总次数")
    """帖子被收藏的总次数"""

    thumbnail_urls: List[str] = Field(description="帖子首楼图片URL列表")
    """帖子首楼图片URL列表"""

    tags: List[str] = Field(default_factory=list, description="帖子关联的标签列表")
    """帖子关联的标签列表"""

    virtual_tags: List[str] = Field(
        default_factory=list, description="帖子匹配的虚拟映射标签名列表"
    )
    """帖子匹配的虚拟映射标签名列表"""

    comment: Optional[str] = Field(None, description="书单主对该帖子的推荐语")
    """书单主对该帖子的推荐语"""

    tournament_participated_at: Optional[UTCDateTime] = Field(
        None, description="参赛时间（赛事专用）"
    )
    """参赛时间（赛事专用）"""

    display_order: int = Field(description="排序权重")
    """排序权重"""

    added_at: UTCDateTime = Field(description="加入书单的时间")
    """加入书单的时间"""

    collected_flag: bool = Field(False, description="当前用户是否收藏了该帖子")
    """当前用户是否收藏了该帖子"""

    viewer_flags: List[ViewerFlag] = Field(
        default_factory=list,
        description="当前查看者与作品的关系标记",
    )
    """当前查看者与作品的关系标记"""

    latest_update: Optional[LatestUpdate] = Field(
        default=None,
        description="作品最新一次正式发布的更新",
    )
    """作品最新一次正式发布的更新"""

    @field_serializer("thread_id", "channel_id", "guild_id")
    def serialize_ids(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)

    model_config = ConfigDict(from_attributes=True)
