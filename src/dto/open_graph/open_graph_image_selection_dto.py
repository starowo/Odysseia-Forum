from pydantic import BaseModel


class OpenGraphImageSelectionDTO(BaseModel):
    """描述一次帖子图片选择与刷新协调的内部结果。"""

    image_url: str | None = None
    refresh_attempted: bool = False
    should_reload: bool = False
    cache_ttl_limit_seconds: int | None = None
