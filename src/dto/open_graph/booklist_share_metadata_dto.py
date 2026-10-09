from pydantic import BaseModel, Field

from dto.open_graph.booklist_share_stats_dto import BooklistShareStatsDTO
from dto.open_graph.open_graph_work_dto import OpenGraphWorkDTO
from shared.utc_datetime import UTCDateTime


class BooklistShareMetadataDTO(BaseModel):
    """描述内部书单或赛事 Open Graph 接口的完整响应。"""

    title: str = Field(description="书单或赛事标题")
    description: str | None = Field(default=None, description="书单或赛事简介")
    cover_image_url: str | None = Field(default=None, description="书单自定义封面 URL")
    author_name: str | None = Field(default=None, description="非匿名书单作者名")
    works: list[OpenGraphWorkDTO] = Field(description="最多五个带图代表作品")
    stats: BooklistShareStatsDTO = Field(description="书单公开统计")
    is_tournament: bool = Field(description="是否为赛事书单")
    created_at: UTCDateTime = Field(description="书单创建时间")
    updated_at: UTCDateTime = Field(description="书单更新时间")
