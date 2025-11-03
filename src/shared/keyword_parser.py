"""
高级搜索关键词解析器
支持以下语法：
- author:作者名 - 搜索指定作者
- "精确关键词" - 精确匹配（用引号包围）
- -排除词 - 排除包含该词的结果
"""

import re
from typing import Tuple, List, Optional


class KeywordParser:
    """解析高级搜索语法"""

    @staticmethod
    def parse(query: str) -> Tuple[Optional[str], List[str], List[str], str]:
        """
        解析搜索关键词字符串

        返回: (author_name, include_keywords, exclude_keywords, remaining_keywords)
        - author_name: 指定的作者名（如果有）
        - include_keywords: 需要包含的关键词列表
        - exclude_keywords: 需要排除的关键词列表
        - remaining_keywords: 剩余的普通关键词
        """
        if not query or not isinstance(query, str):
            return None, [], [], ""

        # 安全处理：移除潜在的SQL注入字符
        query = query.strip()

        author_name = None
        include_keywords = []
        exclude_keywords = []
        remaining_parts = []

        # 正则模式
        # 1. author:xxx 或 author:"xxx xxx"
        author_pattern = r'author:\s*(?:"([^"]+)"|(\S+))'
        # 2. "精确关键词"
        exact_pattern = r'"([^"]+)"'
        # 3. -排除词
        exclude_pattern = r"-(\S+)"

        # 先提取所有特殊语法
        processed_positions = set()

        # 提取 author:
        for match in re.finditer(author_pattern, query, re.IGNORECASE):
            author_name = match.group(1) or match.group(2)
            # 记录已处理的位置
            for i in range(match.start(), match.end()):
                processed_positions.add(i)

        # 提取精确匹配关键词
        for match in re.finditer(exact_pattern, query):
            keyword = match.group(1).strip()
            if keyword and match.start() not in processed_positions:
                include_keywords.append(keyword)
                # 记录已处理的位置
                for i in range(match.start(), match.end()):
                    processed_positions.add(i)

        # 提取排除关键词
        for match in re.finditer(exclude_pattern, query):
            keyword = match.group(1).strip()
            if keyword and match.start() not in processed_positions:
                # 检查不是author:的一部分
                if match.start() == 0 or query[match.start() - 1] != ":":
                    exclude_keywords.append(keyword)
                    # 记录已处理的位置
                    for i in range(match.start(), match.end()):
                        processed_positions.add(i)

        # 提取剩余的普通关键词
        current_word = []
        for i, char in enumerate(query):
            if i in processed_positions:
                if current_word:
                    word = "".join(current_word).strip()
                    if word:
                        remaining_parts.append(word)
                    current_word = []
            else:
                current_word.append(char)

        # 添加最后一个词
        if current_word:
            word = "".join(current_word).strip()
            if word:
                remaining_parts.append(word)

        # 合并剩余关键词
        remaining_keywords = " ".join(remaining_parts).strip()

        return author_name, include_keywords, exclude_keywords, remaining_keywords

    @staticmethod
    def sanitize(text: str) -> str:
        """
        清理文本，防止SQL注入
        移除潜在危险字符，但保留中文和常用标点
        """
        if not text:
            return ""

        # 移除控制字符和NULL字节
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

        # 限制长度
        max_length = 500
        if len(text) > max_length:
            text = text[:max_length]

        return text.strip()
