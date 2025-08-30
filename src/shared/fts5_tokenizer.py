import rjieba
from sqlitefts import fts5


class JiebaRSTokenizer(fts5.FTS5Tokenizer):
    """
    一个使用 jieba-rs 进行分词的 FTS5 分词器。
    """

    def tokenize(self, text, flags=None):
        """
        分词函数，会被SQLite FTS5引擎在索引和查询时调用。

        Args:
            text (str): 需要分词的文本。
            flags (int): SQLite传递的标志位，用于区分不同场景。

        Yields:
            tuple[str, int, int]: 包含词元、起始字节和结束字节的元组。
        """
        # 调用 rjieba.tokenize 进行分词，它返回一个 (word, start, end) 的元组
        for word, start, end in rjieba.tokenize(text):
            yield word, start, end


def register_jieba_tokenizer(conn):
    """
    为给定的 sqlite3 连接注册名为 'jieba' 的 FTS5 分词器。

    conn: 一个标准的 sqlite3 Connection 对象。
    """
    tokenizer_instance = JiebaRSTokenizer()
    tokenizer_handle = fts5.make_fts5_tokenizer(tokenizer_instance)
    fts5.register_tokenizer(conn, "jieba", tokenizer_handle)
