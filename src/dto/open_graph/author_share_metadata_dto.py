from pydantic import BaseModel, Field

from dto.open_graph.author_share_stats_dto import AuthorShareStatsDTO
from dto.open_graph.open_graph_latest_work_dto import OpenGraphLatestWorkDTO
from dto.open_graph.open_graph_work_dto import OpenGraphWorkDTO
from shared.utc_datetime import UTCDateTime


class AuthorShareMetadataDTO(BaseModel):
    """描述内部作者 Open Graph 接口的完整响应。"""

    display_name: str = Field(description="作者显示名")
    avatar_url: str | None = Field(default=None, description="作者头像 URL")
    stats: AuthorShareStatsDTO = Field(description="作者公开作品统计")
    latest_work: OpenGraphLatestWorkDTO | None = Field(
        default=None, description="作者最新公开作品"
    )
    works: list[OpenGraphWorkDTO] = Field(description="最多五个带图代表作品")
    updated_at: UTCDateTime = Field(description="作者资料更新时间")
