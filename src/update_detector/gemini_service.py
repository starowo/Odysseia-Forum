import logging
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一个Discord论坛帖子更新检测助手。你的任务是判断一条消息是否为帖子作者发布的"作品版本更新/发布更新"。

判断标准：
- 消息内容明确提及了新版本、更新、修复、改进、发布等关键词
- 消息包含版本号（如 v1.2、1.0.0 等）
- 消息描述了changelog、更新日志、新增功能、修复内容等
- 消息附带了更新相关的文件（如 .json 配置文件）

不算更新的情况：
- 普通的聊天讨论或回复
- 提问或求助
- 纯粹的感想或评论
- 虽然文字量大但并非版本发布相关

请只回答 "YES" 或 "NO"，不要解释。
"""


class GeminiService:
    """封装 Gemini API 调用，用于判断消息是否为发布更新"""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.0-flash",
        base_url: str = "",
    ):
        client_kwargs: dict = {"api_key": api_key}
        if base_url:
            client_kwargs["http_options"] = types.HttpOptions(base_url=base_url)
        self._client = genai.Client(**client_kwargs)
        self._model = model

    async def is_update_message(
        self, message_content: str, attachment_filenames: Optional[list[str]] = None
    ) -> bool:
        """
        调用 Gemini 判断消息是否为发布更新。

        Args:
            message_content: 消息文本内容
            attachment_filenames: 附件文件名列表（如 json 文件名）

        Returns:
            True 表示判定为发布更新
        """
        user_content = f"消息内容：\n{message_content}"
        if attachment_filenames:
            user_content += f"\n\n附件文件名：{', '.join(attachment_filenames)}"

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=10,
        )

        try:
            chunks: list[str] = []
            stream = await self._client.aio.models.generate_content_stream(
                model=self._model,
                contents=user_content,
                config=config,
            )
            async for chunk in stream:
                if chunk.text:
                    chunks.append(chunk.text)
            result_text = "".join(chunks).strip().upper()
            return result_text == "YES"
        except Exception:
            logger.error("Gemini API 调用失败", exc_info=True)
            return False

    async def close(self):
        """关闭异步客户端"""
        try:
            await self._client.aio.aclose()
        except Exception:
            pass
