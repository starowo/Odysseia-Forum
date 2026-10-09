from pydantic import BaseModel


class SimilarThreadCandidateDTO(BaseModel):
    """缓存中的单个相似帖子候选。"""

    thread_id: int
    matched_tag_count: int
