from pydantic import BaseModel, Field, JsonValue

from shared.utc_datetime import UTCDateTime


class TagAuditResponse(BaseModel):
    """仅向获授权管理人员提供的操作记录。"""

    id: str = Field(description="操作记录内部 ID，以十进制字符串返回")
    """操作记录内部 ID，以十进制字符串返回"""

    type: str = Field(description="操作类型，例如 tag.vote、tag.review；允许后续扩展")
    """操作类型，例如 tag.vote、tag.review；允许后续扩展"""

    actor_id: str | None = Field(
        description="操作者 Discord ID，以字符串返回；系统操作可为空"
    )
    """操作者 Discord ID，以字符串返回；系统操作可为空"""

    tag_id: str | None = Field(
        description="关联标签内部 ID，以字符串返回；未关联时为空"
    )
    """关联标签内部 ID，以字符串返回；未关联时为空"""

    detail: dict[str, JsonValue] = Field(
        description="可扩展 JSON 详情，字段随操作类型变化"
    )
    """可扩展 JSON 详情，字段随操作类型变化"""

    created_at: UTCDateTime = Field(description="记录创建时间（UTC）")
    """记录创建时间（UTC）"""
