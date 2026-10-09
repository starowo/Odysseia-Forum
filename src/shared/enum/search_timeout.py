from enum import Enum


class SearchTimeout(float, Enum):
    """搜索超时默认值（秒）"""

    SEARCH = 20.0  # 常规搜索：复杂查询留有充足余量，同时防止事件循环长期阻塞
    FTS_TOKENIZE = 3.0  # jieba 分词：单次分词正常 <100ms
    SUGGESTION = 5.0  # 搜索建议：查询较简单
    SIMILAR_THREADS = 15.0  # 相似帖子：内部循环多次搜索
    THREAD_DETAIL = 5.0  # 帖子详情：单条查询
