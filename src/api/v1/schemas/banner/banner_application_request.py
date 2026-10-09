"""Banner申请请求Schema"""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class BannerApplicationRequest(BaseModel):
    """Banner申请请求模型"""

    thread_link: str = Field(
        ...,
        min_length=17,
        max_length=150,
        description="Discord 跳转链接（https://discord.com/channels/{guild_id}/{id}）或纯数字 ID",
    )
    cover_image_url: str | None = Field(
        default=None,
        description="可选封面图链接；帖子留空时动态使用当前首图，频道不可留空",
    )
    target_scope: str = Field(
        ..., description="目标范围：'global'表示全频道，或具体频道ID"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_thread_link(cls, data: Any) -> Any:
        """兼容旧接口：将 thread_id 自动转换为 thread_link"""
        if isinstance(data, dict):
            if "thread_id" in data and "thread_link" not in data:
                data = {**data, "thread_link": data.pop("thread_id")}
            elif "thread_id" in data:
                data.pop("thread_id")
        return data
