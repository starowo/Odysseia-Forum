"""Author 数据传输对象 — 安全用于 session 外。"""

from typing import Optional

from pydantic import BaseModel, Field


class AuthorDTO(BaseModel):
    """Author 的轻量 DTO。"""

    id: int = Field(description="作者的 Discord 用户 ID")
    name: str = Field(description="作者的唯一用户名")
    global_name: Optional[str] = Field(default=None, description="作者的全局显示名称")
    display_name: str = Field(description="作者的显示名称")
    avatar_url: Optional[str] = Field(default=None, description="作者头像的 URL")

    @staticmethod
    def from_orm(author) -> "AuthorDTO":
        """从 Author ORM 对象构建 AuthorDTO（须在 session 内调用）。"""
        return AuthorDTO(
            id=author.id,
            name=author.name,
            global_name=author.global_name,
            display_name=author.display_name,
            avatar_url=author.avatar_url,
        )
