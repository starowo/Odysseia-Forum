from pydantic import BaseModel, Field, field_serializer


class TournamentInfo(BaseModel):
    """赛事书单简要信息"""

    booklist_id: int = Field(description="赛事书单ID")
    """赛事书单ID"""

    booklist_name: str = Field(description="赛事书单名")
    """赛事书单名"""

    @field_serializer("booklist_id")
    def serialize_id(self, value: int) -> str:
        """将 Discord ID 序列化为字符串，避免 JavaScript 精度丢失"""
        return str(value)
