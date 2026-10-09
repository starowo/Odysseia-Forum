from __future__ import annotations

import html
import re


class OpenGraphTextFormatter:
    """将用户文本清洗为适合分享卡片展示的纯文本。"""

    _MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
    _MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]*\)")
    _HTML_TAG_PATTERN = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")
    _MARKDOWN_CONTROL_PATTERN = re.compile(r"[`*_~>#|]+")
    _WHITESPACE_PATTERN = re.compile(r"\s+")

    @classmethod
    def format(
        cls,
        value: str | None,
        *,
        limit: int,
        empty_value: str | None,
    ) -> str | None:
        """清洗并按包含省略号的字符上限截断文本。"""
        # 先解码实体，确保实体生成的标签也按真实 HTML 标签处理。
        cleaned = html.unescape(value or "")
        cleaned = cls._MARKDOWN_IMAGE_PATTERN.sub(r"\1", cleaned)
        cleaned = cls._MARKDOWN_LINK_PATTERN.sub(r"\1", cleaned)
        cleaned = cls._HTML_TAG_PATTERN.sub(" ", cleaned)

        # 删除展示用 Markdown 控制符，但保留链接标签和普通用户文本。
        cleaned = cls._MARKDOWN_CONTROL_PATTERN.sub("", cleaned)
        cleaned = cls._WHITESPACE_PATTERN.sub(" ", cleaned).strip()
        if not cleaned:
            return empty_value

        # 省略号计入调用方指定的最终字符上限。
        if len(cleaned) > limit:
            if limit <= 1:
                return "…"[:limit]
            cleaned = f"{cleaned[: limit - 1]}…"
        return cleaned
