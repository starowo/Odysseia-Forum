from math import ceil

from dto.update_detector import TokenEstimate


class TokenEstimator:
    """使用固定启发式规则估算聊天请求的 Token 数量。"""

    CHAT_OVERHEAD_TOKENS = 16

    def estimate(
        self,
        system_content: str,
        user_content: str,
        max_output_tokens: int,
    ) -> TokenEstimate:
        """估算完整提示词 Token 及单次请求的输出上界。"""
        complete_content = system_content + user_content
        ascii_count = sum(character.isascii() for character in complete_content)
        non_ascii_count = len(complete_content) - ascii_count

        # 对每次请求独立向上取整，避免聚合后低估短 ASCII 片段。
        content_tokens = non_ascii_count + ceil(ascii_count / 4)
        prompt_tokens = content_tokens + self.CHAT_OVERHEAD_TOKENS
        return TokenEstimate(
            ascii_character_count=ascii_count,
            non_ascii_character_count=non_ascii_count,
            estimated_content_tokens=content_tokens,
            chat_overhead_tokens=self.CHAT_OVERHEAD_TOKENS,
            estimated_prompt_tokens=prompt_tokens,
            estimated_completion_tokens_upper_bound=max_output_tokens,
            estimated_total_tokens_upper_bound=prompt_tokens + max_output_tokens,
        )
