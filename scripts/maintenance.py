"""PostgreSQL 定期维护脚本。

用法：
  docker compose exec -T odysseia-forum-bot uv run scripts/maintenance.py --report
"""

import os
import subprocess
from datetime import datetime
from urllib.parse import urlparse


def pg_components():
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://odysseia:changeme@localhost:5432/odysseia",
    )
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    u = urlparse(url)
    return (
        u.hostname or "localhost",
        str(u.port or 5432),
        u.path.lstrip("/"),
        u.username or "",
        u.password or "",
    )


def run_psql(sql: str) -> str:
    host, port, db, user, pw = pg_components()
    env = {**os.environ, "PGPASSWORD": pw}
    r = subprocess.run(
        ["psql", "-h", host, "-p", port, "-d", db, "-U", user, "-c", sql],
        capture_output=True,
        text=True,
        env=env,
    )
    return r.stdout


def cmd_vacuum():
    """VACUUM ANALYZE 关键表（不锁表，回收空间 + 更新统计）"""
    tables = [
        "thread",
        "thread_follow",
        "booklist",
        "booklist_item",
        "thread_tag_link",
    ]
    for t in tables:
        print(f"[{datetime.now()}] VACUUM ANALYZE {t}...")
        print(run_psql(f"VACUUM (ANALYZE, VERBOSE) {t}"))
    print(f"[{datetime.now()}] VACUUM 完成")


def cmd_analyze():
    """全库统计信息更新（比 VACUUM 轻量，只读采样）"""
    print(f"[{datetime.now()}] ANALYZE 全库...")
    print(run_psql("ANALYZE VERBOSE"))
    print(f"[{datetime.now()}] ANALYZE 完成")


def cmd_reindex():
    """重建 GIN 索引（CONCURRENTLY = 不锁表）"""
    indexes = ["ix_thread_search_vector", "ix_booklist_search_vector"]
    for idx in indexes:
        print(f"[{datetime.now()}] REINDEX INDEX CONCURRENTLY {idx}...")
        result = run_psql(f"REINDEX INDEX CONCURRENTLY {idx}")
        print(result)
        if "ERROR" in result:
            print(f"  ⚠ REINDEX 失败，检查是否需要 DROP INDEX CONCURRENTLY {idx}")
    print(f"[{datetime.now()}] REINDEX 完成")


def cmd_report():
    print("=" * 60)
    print("表大小排名 (TOP 10)")
    print("=" * 60)
    print(
        run_psql(
            """
        SELECT relname AS table_name,
               pg_size_pretty(pg_total_relation_size(relid)) AS total,
               pg_size_pretty(pg_relation_size(relid)) AS data,
               pg_size_pretty(pg_indexes_size(relid)) AS indexes,
               n_live_tup AS live_rows
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
        LIMIT 10;
    """
        )
    )

    print("=" * 60)
    print("死元组统计（n_dead_tup > 100）")
    print("=" * 60)
    print(
        run_psql(
            """
        SELECT relname, n_dead_tup, n_live_tup,
               round(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 1) AS dead_pct,
               last_autovacuum, last_autoanalyze
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 100
        ORDER BY n_dead_tup DESC;
    """
        )
    )

    print("=" * 60)
    print("未使用的索引（idx_scan = 0，排除主键）")
    print("=" * 60)
    print(
        run_psql(
            """
        SELECT relname AS table_name, indexrelname AS index_name,
               pg_size_pretty(pg_relation_size(indexrelid)) AS size,
               idx_scan, idx_tup_read
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
          AND indexrelname NOT LIKE '%pkey%'
        ORDER BY pg_relation_size(indexrelid) DESC;
    """
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--vacuum", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.report:
        cmd_report()
    if args.analyze:
        cmd_analyze()
    if args.vacuum:
        cmd_vacuum()
    if args.reindex:
        cmd_reindex()
