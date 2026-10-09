from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class AuthorSuggestion(BaseModel):
    """搜索建议中的作者模型"""

    id: int = Field(description="作者 Discord ID")
    name: str = Field(description="用户名")
    display_name: str = Field(description="显示名称")
    avatar_url: Optional[str] = Field(default=None, description="头像 URL")

    @field_serializer("id")
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免前端精度丢失"""
        return str(value)

    model_config = ConfigDict(from_attributes=True)
