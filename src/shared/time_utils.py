"""时间工具函数。

提供 UTC 时间获取函数，替代 Python 3.12 中已废弃的 datetime.utcnow()。
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """返回当前 UTC 时间的 naive datetime。

    替代已废弃的 datetime.utcnow()。
    使用 datetime.now(UTC) 获取时间后剥离时区，生成与旧 utcnow() 行为完全一致的
    naive datetime，与 PG TIMESTAMP WITHOUT TIME ZONE 列兼容。
    """
    return datetime.now(UTC).replace(tzinfo=None)
