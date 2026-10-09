from typing import Any

from pydantic import BaseModel, ConfigDict


class FTSResultDTO(BaseModel):
    """
    关键词 FTS 全文搜索结果的条件对象。

    将 search_vector @@ tsquery 条件直接嵌入 WHERE 子句，
    让 PG 优化器能用 GIN 索引而不是回退到全表扫描。
    """

    include_conditions: list = []  # 每个 AND 组一个 search_vector @@ tsquery 条件
    exclude_condition: Any = (
        None  # 排除关键词的 search_vector @@ tsquery 条件，无排除词则为 None
    )
    has_include: bool = False
    has_exclude: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)
