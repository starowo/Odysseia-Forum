"""全文搜索文本分词工具。"""

import rjieba

from shared.search_normalization import normalize_search_text


def build_search_vector_text(title: str | None, excerpt: str | None) -> str | None:
    """用 rjieba 对 title + excerpt 分词，返回空格连接的 token 字符串。

    用于填充 PostgreSQL search_vector 列（通过 to_tsvector('simple', ...)）。
    to_tsvector('simple') 按词顺序分配位置，支持 <-> 和 <N> 邻近搜索。
    所有 token 转为小写以确保大小写不敏感匹配。
    """
    parts = []
    if title:
        parts.append(title)
    if excerpt:
        parts.append(excerpt)
    if not parts:
        return None
    # 仅规范化搜索副本，保留数据库中的原文。
    combined = normalize_search_text(" ".join(parts))
    tokens = list(rjieba.cut(combined))
    filtered = [t.lower().strip() for t in tokens if t.strip()]
    return " ".join(filtered) if filtered else None
