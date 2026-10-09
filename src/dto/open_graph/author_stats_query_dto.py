from pydantic import BaseModel


class AuthorStatsQueryDTO(BaseModel):
    """承载作者公开作品的聚合统计查询结果。"""

    thread_count: int
    reaction_count: int
    reply_count: int
