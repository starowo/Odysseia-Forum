from pydantic import BaseModel, Field
from shared.request_id import RequestId


class TagSelectionRequest(BaseModel):
    """作者或管理组提交的完整本地绑定标签集合。"""

    version: str = Field(
        description="读取目标标签时返回的版本标记，提交时原样传回；用于防止覆盖并发修改，过期返回 409 stale_version"
    )
    """GET 返回的标签集合版本标记，原样传回用于并发校验"""

    tag_ids: list[RequestId] = Field(
        max_length=100,
        description="目标完整本地绑定标签内部 ID 集合，接受十进制字符串或整数；帖子仅允许自定义实体，书单也允许 DC 实体；不提交 discord_sync 只读绑定，未传入的本地绑定将解绑，空列表清空本地绑定",
    )
    """目标完整本地绑定标签 ID 集合；空列表清空本地绑定，保留 DC 同步只读绑定"""
