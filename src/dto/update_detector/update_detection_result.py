from typing import Literal

from pydantic import BaseModel, Field


class UpdateDetectionResult(BaseModel):
    """承载一次 DeepSeek 更新检测的判断与用量结果。"""

    api_success: bool = Field(
        default=False, description="DeepSeek 接口是否成功返回可解析响应"
    )
    """DeepSeek 接口是否成功返回可解析响应"""

    decision: Literal["YES", "NO"] | None = Field(
        default=None, description="模型给出的严格更新判断结果"
    )
    """模型给出的严格更新判断结果"""

    truncated: bool = Field(
        default=False, description="模型输出是否因达到长度上限而截断"
    )
    """模型输出是否因达到长度上限而截断"""

    prompt_tokens: int | None = Field(
        default=None, ge=0, description="接口返回的真实输入 Token 数量"
    )
    """接口返回的真实输入 Token 数量"""

    completion_tokens: int | None = Field(
        default=None, ge=0, description="接口返回的真实生成 Token 数量"
    )
    """接口返回的真实生成 Token 数量"""

    total_tokens: int | None = Field(
        default=None, ge=0, description="接口返回的真实总 Token 数量"
    )
    """接口返回的真实总 Token 数量"""

    @property
    def is_update(self) -> bool:
        """返回模型是否有效判定为更新消息。"""
        return self.api_success and not self.truncated and self.decision == "YES"

    @property
    def usage_missing(self) -> bool:
        """返回响应是否缺少完整 Token usage。"""
        return any(
            value is None
            for value in (
                self.prompt_tokens,
                self.completion_tokens,
                self.total_tokens,
            )
        )
