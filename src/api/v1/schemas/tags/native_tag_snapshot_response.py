from typing import Literal

from pydantic import Field

from api.v1.schemas.tags.tag_response import TagResponse


class NativeTagSnapshotResponse(TagResponse):
    """目标上的只读 Discord 原生标签。"""

    source: Literal["discord"] = Field(description="来源固定为 discord")
    """来源固定为 discord"""

    binding_source: Literal["discord_sync"] = Field(
        description="绑定来源，用于区分只读同步和本地治理"
    )
    """绑定来源判别字段"""

    readonly: Literal[True] = Field(description="固定为 true，原生标签在本项目不可修改")
    """固定为 true，原生标签在本项目不可修改"""

    discord_source_id: str = Field(
        description="此帖子绑定所依据的 DC 来源记录 ID，可在 discord_sources 中定位"
    )
    """此绑定的具体 DC 来源"""
