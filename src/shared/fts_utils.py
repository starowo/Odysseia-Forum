"""PostgreSQL 全文搜索（FTS）共享工具。

从 thread_repository / booklist_repository 提取的通用 tsquery 构建逻辑，
接受 search_vector 列引用作为参数，供任何带 TSVECTOR 列的表复用。
"""

import asyncio
import hashlib
import json
import logging
import re

import rjieba
from sqlalchemy import literal_column

from dto.search.fts_result_dto import FTSResultDTO
from shared.enum import CacheKeys, SearchTimeout
from shared.search_normalization import (
    SEARCH_NORMALIZATION_VERSION,
    normalize_search_text,
)

logger = logging.getLogger(__name__)


# ── 分词 & tsquery 构建辅助 ──────────────────────────────────


def batch_cut(keywords: list[str]) -> list[list[str]]:
    """批量 rjieba 分词"""
    return [list(rjieba.cut(kw)) for kw in keywords]


def escape_tsquery_token(token: str) -> str:
    """转义 token 中可能破坏 PostgreSQL tsquery 语法的单引号和反斜杠。"""
    token = token.replace("\\", "\\\\")  # 先转义反斜杠
    return token.replace("'", "''")  # 再转义单引号


def tokens_to_tsquery_and(tokens: list[str]) -> str:
    """将 token 列表转为 PostgreSQL tsquery AND 表达式。

    最后一个 token 带 :* 前缀匹配后缀。
    例如 ['搬运', '工'] → '搬运 & 工:*'
    """
    if not tokens:
        return ""
    escaped = [escape_tsquery_token(t.lower()) for t in tokens]
    parts = [f"'{t}'" for t in escaped[:-1]]
    parts.append(f"'{escaped[-1]}':*")
    return " & ".join(parts)


def build_exemption_tsquery(
    first_token: str, markers: list[str], proximity: int = 4
) -> str:
    """构建豁免标记 tsquery：检查豁免标记是否在排除词 ±N 词位内。

    使用双向 <d> 距离运算符组合（d ∈ [1, proximity]），
    限制豁免标记仅在排除关键词附近（N 个词位内）才生效。
    to_tsvector('simple', ...) 按词顺序分配位置，支持邻近搜索。
    所有字符（包括非 BMP emoji 如 🈲）均可通过 ::tsquery cast 保留。
    """
    first = escape_tsquery_token(first_token)
    clauses = []
    for marker in markers:
        m = escape_tsquery_token(marker)
        for d in range(1, proximity + 1):
            clauses.append(f"'{first}' <{d}> '{m}'")
            clauses.append(f"'{m}' <{d}> '{first}'")
    return " | ".join(clauses) if clauses else ""


# ── 核心 FTS 条件构建 ────────────────────────────────────────


async def build_fts_conditions(
    search_vector_column,
    keywords: str | None,
    exclude_keywords: str | None,
    exemption_markers: list[str] | None = None,
    redis_client=None,
) -> FTSResultDTO:
    """构建 PostgreSQL FTS 全文搜索条件。

    使用 rjieba 分词后构建 tsquery 表达式，返回可直接嵌入 WHERE 子句的
    ``search_vector @@ tsquery`` 条件对象，让 PG 优化器使用 GIN 索引。

    通过 redis_client 缓存分词后的 tsquery 字符串（TTL 1h），
    避免重复 jieba 分词开销。

    Parameters:
        search_vector_column: SQLAlchemy 列对象（如 ``Thread.search_vector``）
        keywords: 正选关键词（支持逗号 AND / 斜杠 OR / 双引号精确短语）
        exclude_keywords: 排除关键词（空格/逗号/斜杠分隔）
        exemption_markers: 排除豁免标记列表（默认 ``["禁", "🈲"]``）
        redis_client: 可选 Redis 客户端，用于缓存 tsquery 字符串

    Returns:
        FTSResultDTO: 包含 include_conditions 和 exclude_condition
    """
    # 在解析原有语法和分词前转换繁体搜索关键词为简体中文
    keywords = normalize_search_text(keywords) if keywords else keywords
    exclude_keywords = (
        normalize_search_text(exclude_keywords)
        if exclude_keywords
        else exclude_keywords
    )
    markers = [
        normalize_search_text(marker).lower()
        for marker in (
            exemption_markers if exemption_markers is not None else ["禁", "🈲"]
        )
    ]

    # ── 尝试从 Redis 缓存读取已构建的 tsquery 字符串 ──
    cache_key = None
    if redis_client and (keywords or exclude_keywords):
        # 规则版本和有效豁免标记进入结构化摘要，隔离旧缓存及 None/空列表。
        raw = json.dumps(
            [SEARCH_NORMALIZATION_VERSION, keywords, exclude_keywords, markers],
            ensure_ascii=False,
        )
        prefix = (keywords or "none")[:5]
        cache_key = CacheKeys.FTS_TSQUERY_RESULT.format(
            prefix=prefix,
            hash=hashlib.md5(raw.encode()).hexdigest(),
        )
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                include_conditions: list = []
                for tsq in data.get("ig", []):
                    cond = search_vector_column.op("@@")(
                        literal_column(f"$${tsq}$$::tsquery")
                    )
                    include_conditions.append(cond)
                exclude_condition = None
                if data.get("eg"):
                    exclude_condition = search_vector_column.op("@@")(
                        literal_column(f"$${data['eg']}$$::tsquery")
                    )
                return FTSResultDTO(
                    include_conditions=include_conditions,
                    exclude_condition=exclude_condition,
                    has_include=bool(include_conditions),
                    has_exclude=exclude_condition is not None,
                )
        except Exception:
            pass  # 缓存失败不影响搜索，继续走正常流程

    loop = asyncio.get_running_loop()
    exclude_condition = None
    include_conditions: list = []

    # 收集构建的 tsquery 字符串，用于回填缓存
    cached_include_tsqueries: list[str] = []
    cached_exclude_tsquery: str | None = None

    # ============ 反选关键词：构建排除子查询 ============
    if exclude_keywords:
        exclude_keywords_list = [
            kw.strip()
            for kw in re.split(r"[,，/\\\s]+", exclude_keywords)
            if kw.strip()
        ]

        all_exclude_tsqueries: list[str] = []
        try:
            all_raw_tokens = await asyncio.wait_for(
                loop.run_in_executor(None, batch_cut, exclude_keywords_list),
                timeout=SearchTimeout.FTS_TOKENIZE.value,
            )
        except asyncio.TimeoutError:
            logger.warning("jieba 分词超时（排除关键词）")
            all_raw_tokens = [[] for _ in exclude_keywords_list]

        for keyword, raw_tokens in zip(exclude_keywords_list, all_raw_tokens):
            tokens = [t.strip() for t in raw_tokens if t.strip()]
            if not tokens:
                continue

            # 构建 PostgreSQL tsquery：tokens 用 & 连接，最后一个带 :* 前缀匹配
            tsquery_and = tokens_to_tsquery_and(tokens)

            if markers:
                # 构建豁免子句：token <4> marker（双向）
                exemption_tsq = build_exemption_tsquery(tokens[0], markers)
                all_exclude_tsqueries.append(f"({tsquery_and}) &! ({exemption_tsq})")
            else:
                all_exclude_tsqueries.append(f"({tsquery_and})")

        # 所有排除词用 | 连接（命中任一即排除）
        if all_exclude_tsqueries:
            final_exclude_tsquery = " | ".join(all_exclude_tsqueries)
            cached_exclude_tsquery = final_exclude_tsquery
            exclude_condition = search_vector_column.op("@@")(
                literal_column(f"$${final_exclude_tsquery}$$::tsquery")
            )

    # ============ 正选关键词：每个 AND 组构建一个子查询 ============
    has_any_include = False
    if keywords:
        # 按逗号拆分为多个 AND 组，各关键词组之间取交集
        keywords_str = keywords.replace("，", ",").replace("／", "/").replace("\\", "/")
        and_groups = [
            group.strip() for group in keywords_str.split(",") if group.strip()
        ]

        # 收集所有需要分词的普通关键词，一次批量提交到线程池
        _jieba_inputs = []
        for group in and_groups:
            for kw in group.split("/"):
                kw = kw.strip()
                if not kw:
                    continue
                if not (kw.startswith('"') and kw.endswith('"') and len(kw) > 2):
                    _jieba_inputs.append(kw)

        _token_map = {}
        if _jieba_inputs:
            try:
                _all_raw = await asyncio.wait_for(
                    loop.run_in_executor(None, batch_cut, _jieba_inputs),
                    timeout=SearchTimeout.FTS_TOKENIZE.value,
                )
            except asyncio.TimeoutError:
                logger.warning("jieba 分词超时（正选关键词）")
                _all_raw = [[] for _ in _jieba_inputs]

            for kw, raw_tokens in zip(_jieba_inputs, _all_raw):
                tokens = [t.strip() for t in raw_tokens if t.strip()]
                if tokens:
                    _token_map[kw] = tokens

        for group in and_groups:
            or_tsquery_parts = []
            for kw in group.split("/"):
                kw = kw.strip()
                if not kw:
                    continue

                # 双引号关键词也使用规范化副本，所有 token 精确匹配且需同时存在
                if kw.startswith('"') and kw.endswith('"') and len(kw) > 2:
                    exact_kw = kw[1:-1].strip().replace('"', "")
                    if exact_kw:
                        exact_tokens = list(rjieba.cut(exact_kw))
                        clean_tokens = [
                            t.strip().lower() for t in exact_tokens if t.strip()
                        ]
                        if clean_tokens:
                            phrase = " & ".join(
                                f"'{escape_tsquery_token(t)}'" for t in clean_tokens
                            )
                            or_tsquery_parts.append(f"({phrase})")
                else:
                    tokens = _token_map.get(kw)
                    if tokens:
                        tsq = tokens_to_tsquery_and(tokens)
                        or_tsquery_parts.append(f"({tsq})")

            if or_tsquery_parts:
                group_tsquery = " | ".join(or_tsquery_parts)
                cached_include_tsqueries.append(group_tsquery)
                cond = search_vector_column.op("@@")(
                    literal_column(f"$${group_tsquery}$$::tsquery")
                )
                include_conditions.append(cond)
                has_any_include = True

    # ── 回填 Redis 缓存 ──
    if cache_key and redis_client:
        try:
            cache_data: dict = {"ig": cached_include_tsqueries}
            if cached_exclude_tsquery:
                cache_data["eg"] = cached_exclude_tsquery
            await redis_client.setex(
                cache_key, 3600, json.dumps(cache_data, ensure_ascii=False)
            )
        except Exception:
            pass

    return FTSResultDTO(
        include_conditions=include_conditions,
        exclude_condition=exclude_condition,
        has_include=has_any_include,
        has_exclude=exclude_condition is not None,
    )
