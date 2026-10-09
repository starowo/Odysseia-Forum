from pydantic import BaseModel, Field


class TokenEstimate(BaseModel):
    """描述一次更新检测请求的本地 Token 估算。"""

    ascii_character_count: int = Field(
        ge=0, description="完整提示词中的 ASCII 字符数量"
    )
    """完整提示词中的 ASCII 字符数量"""

    non_ascii_character_count: int = Field(
        ge=0, description="完整提示词中的非 ASCII 字符数量"
    )
    """完整提示词中的非 ASCII 字符数量"""

    estimated_content_tokens: int = Field(
        ge=0, description="按字符规则估算的内容 Token 数量"
    )
    """按字符规则估算的内容 Token 数量"""

    chat_overhead_tokens: int = Field(
        ge=0, description="聊天消息模板产生的固定 Token 开销"
    )
    """聊天消息模板产生的固定 Token 开销"""

    estimated_prompt_tokens: int = Field(ge=0, description="内容估算与聊天模板开销之和")
    """内容估算与聊天模板开销之和"""

    estimated_completion_tokens_upper_bound: int = Field(
        ge=0, description="单次请求允许生成的最大 Token 数量"
    )
    """单次请求允许生成的最大 Token 数量"""

    estimated_total_tokens_upper_bound: int = Field(
        ge=0, description="输入估算与输出上界之和"
    )
    """输入估算与输出上界之和"""
