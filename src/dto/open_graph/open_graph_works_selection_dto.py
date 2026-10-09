from pydantic import BaseModel, Field

from dto.open_graph.open_graph_work_dto import OpenGraphWorkDTO


class OpenGraphWorksSelectionDTO(BaseModel):
    """描述多作品图片选择、来源与缓存限制的内部结果。"""

    works: list[OpenGraphWorkDTO] = Field(default_factory=list)
    source_thread_ids: list[int] = Field(default_factory=list)
    refresh_attempted: bool = False
    cache_ttl_limit_seconds: int | None = None
