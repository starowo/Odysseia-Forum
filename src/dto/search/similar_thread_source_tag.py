from pydantic import BaseModel


class SimilarThreadSourceTagDTO(BaseModel):
    """相似推荐冷构建所需的源帖标签投影。"""

    tag_id: int
    tag_name: str
