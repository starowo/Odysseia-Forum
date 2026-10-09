from pydantic import BaseModel, ConfigDict, Field


class BooklistSuggestion(BaseModel):
    """搜索建议中的书单模型"""

    id: int = Field(description="书单 ID")
    title: str = Field(description="书单标题")
    item_count: int = Field(description="帖子数量")

    model_config = ConfigDict(from_attributes=True)
