from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from dto.author.author_stats import AuthorStats


class AuthorProfileResponse(BaseModel):
    """作者档案详情及统计数据的响应模型。"""

    id: int = Field(description="作者的 Discord 用户 ID")
    """作者的 Discord 用户 ID"""

    name: str = Field(description="作者的唯一用户名")
    """作者的唯一用户名"""

    global_name: Optional[str] = Field(description="作者的全局显示名称")
    """作者的全局显示名称"""

    display_name: str = Field(description="作者的服务器内显示名称")
    """作者的服务器内显示名称"""

    avatar_url: Optional[str] = Field(description="作者头像的 URL")
    """作者头像的 URL"""

    stats: AuthorStats = Field(description="作者相关的统计摘要")
    """作者相关的统计摘要"""

    @field_serializer("id")
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失。"""
        return str(value)

    model_config = ConfigDict(from_attributes=True)
