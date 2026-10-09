from pydantic import BaseModel, Field


class OpenGraphAuthorDTO(BaseModel):
    """描述帖子分享卡片中的作者公开信息。"""

    display_name: str = Field(description="作者显示名")
    avatar_url: str | None = Field(default=None, description="作者头像 URL")
