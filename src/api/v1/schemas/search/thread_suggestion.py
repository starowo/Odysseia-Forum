from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ThreadSuggestion(BaseModel):
    """搜索建议中的帖子模型"""

    thread_id: int = Field(description="帖子 Discord ID")
    title: str = Field(description="帖子标题")
    channel_id: int = Field(description="频道 ID")
    guild_id: int = Field(description="服务器 ID")

    @field_serializer("thread_id", "channel_id", "guild_id")
    def serialize_id(self, value: int) -> str:
        return str(value)

    model_config = ConfigDict(from_attributes=True)
