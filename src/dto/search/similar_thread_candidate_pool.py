from pydantic import BaseModel, Field

from dto.search.similar_thread_candidate import SimilarThreadCandidateDTO


class SimilarThreadCandidatePoolDTO(BaseModel):
    """可跨用户共享的相似帖子候选池。"""

    generated_at: float
    candidates: list[SimilarThreadCandidateDTO] = Field(default_factory=list)
