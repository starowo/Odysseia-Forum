"""历史搜索向量回填所需的原文快照。"""

from pydantic import BaseModel


class SearchVectorSourceDTO(BaseModel):
    """跨事务传递原文和由原文计算的搜索分词。"""

    id: int
    """帖子或书单的数据库主键，用于分页和条件更新。"""

    title: str | None
    """读取时的标题原文快照，用于核对并发修改。"""

    body: str | None
    """正文原文快照，对应帖子首条消息摘要或书单简介。"""

    tokens: str | None = None
    """规范化分词后以空格连接的文本，未计算或无有效词项时为 None。"""
