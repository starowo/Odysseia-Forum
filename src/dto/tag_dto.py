"""Tag 数据传输对象 — 安全用于 session 外。"""

from pydantic import BaseModel, Field


class TagDTO(BaseModel):
    """Tag 的轻量 DTO。"""

    id: int = Field(description="内部标签 ID")
    """本项目的内部标签 ID，不是 Discord 标签 ID"""

    name: str = Field(description="标签名称")
    """标签名称"""

    @staticmethod
    def from_orm(tag) -> "TagDTO":
        """从 Tag ORM 对象构建 TagDTO（须在 session 内调用）。"""
        return TagDTO(
            id=tag.id,
            name=tag.name,
        )
