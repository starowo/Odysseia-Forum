from pydantic import BaseModel, Field

from dto.search.similar_thread_source_tag import SimilarThreadSourceTagDTO


class SimilarThreadSourceDTO(BaseModel):
    """相似推荐冷构建所需的源帖轻量投影。"""

    thread_id: int
    tags: list[SimilarThreadSourceTagDTO] = Field(default_factory=list)
