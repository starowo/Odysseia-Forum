import logging
from typing import Literal

import httpx

from dto.update_detector import UpdateDetectionResult

logger = logging.getLogger(__name__)


class DeepSeekService:
    """通过 OpenAI Chat Completions 协议调用 DeepSeek 更新检测。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        thinking_enabled: bool,
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> None:
        self._model = model
        self._thinking_enabled = thinking_enabled
        self._max_output_tokens = max_output_tokens
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout_seconds,
        )

    async def detect_update(
        self,
        system_content: str,
        user_content: str,
    ) -> UpdateDetectionResult:
        """请求 DeepSeek 并返回严格的 YES/NO 判断及 Token usage。"""
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "thinking": {"type": "enabled" if self._thinking_enabled else "disabled"},
            "max_tokens": self._max_output_tokens,
            "stream": False,
        }

        try:
            response = await self._client.post(self._endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            choice = data["choices"][0]
            finish_reason = choice.get("finish_reason")
            raw_content = str(choice["message"].get("content") or "")
            normalized_content = raw_content.strip().upper()
            usage = data.get("usage") or {}
            truncated = finish_reason == "length"
            # 仅将严格匹配的模型输出转换为有效判断。
            decision: Literal["YES", "NO"] | None = None
            if not truncated and normalized_content == "YES":
                decision = "YES"
            elif not truncated and normalized_content == "NO":
                decision = "NO"
            return UpdateDetectionResult(
                api_success=True,
                decision=decision,
                truncated=truncated,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            )
        except httpx.HTTPStatusError as error:
            logger.error(
                "DeepSeek API 返回错误状态: status=%s",
                error.response.status_code,
            )
        except (httpx.HTTPError, IndexError, KeyError, TypeError, ValueError):
            logger.error("DeepSeek API 调用或响应解析失败", exc_info=True)
        return UpdateDetectionResult()

    async def close(self) -> None:
        """关闭异步 HTTP 客户端。"""
        await self._client.aclose()
