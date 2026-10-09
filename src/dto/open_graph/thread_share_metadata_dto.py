from pydantic import BaseModel, Field

from dto.open_graph.open_graph_author_dto import OpenGraphAuthorDTO
from dto.open_graph.thread_share_stats_dto import ThreadShareStatsDTO
from shared.utc_datetime import UTCDateTime


class ThreadShareMetadataDTO(BaseModel):
    """描述内部帖子 Open Graph 接口的完整响应。"""

    title: str = Field(description="帖子标题")
    description: str | None = Field(default=None, description="帖子摘要")
    image_url: str | None = Field(default=None, description="当前有效的帖子图片 URL")
    author: OpenGraphAuthorDTO = Field(description="帖子作者公开信息")
    stats: ThreadShareStatsDTO = Field(description="帖子公开统计")
    created_at: UTCDateTime = Field(description="帖子创建时间")
    updated_at: UTCDateTime = Field(description="帖子更新时间")
