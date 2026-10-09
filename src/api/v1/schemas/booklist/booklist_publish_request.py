from pydantic import BaseModel, Field


class BooklistPublishRequest(BaseModel):
    """书单发布请求"""

    thread_url: str = Field(description="Discord 讨论帖完整 URL")
    """Discord 讨论帖完整 URL（格式: https://discord.com/channels/{guild_id}/{thread_id}）"""
