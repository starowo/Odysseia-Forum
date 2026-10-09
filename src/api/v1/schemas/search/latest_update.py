from pydantic import BaseModel, Field

from shared.utc_datetime import UTCDateTime


class LatestUpdate(BaseModel):
    """API 响应中的作品最新更新。"""

    id: int = Field(description="作品更新的数据库主键 ID")
    """作品更新的数据库主键 ID"""

    description: str = Field(description="作者提交的更新说明")
    """作者提交的更新说明"""

    version: str | None = Field(default=None, description="可选的人类可读版本号")
    """可选的人类可读版本号"""

    message_link: str | None = Field(
        default=None,
        description="Discord 更新来源消息链接",
    )
    """Discord 更新来源消息链接"""

    source_message_at: UTCDateTime = Field(description="Discord 来源消息发布时间")
    """Discord 来源消息发布时间"""

    published_at: UTCDateTime = Field(description="更新正式发布到索引页的时间")
    """更新正式发布到索引页的时间"""
