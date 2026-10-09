"""
SQLite → PostgreSQL 数据迁移脚本（一次性使用）。

用法：
    1. 确保 PostgreSQL 正在运行
    2. 设置环境变量或修改下方配置
    3. python scripts/migrate_sqlite_to_pg.py

脚本会自动完成：
    - 建表（若不存在）
    - 数据导入
    - search_vector 分词填充
    - GIN 索引创建
    - 序列重置

环境变量：
    SQLITE_PATH: SQLite 数据库路径（默认 data/database.db）
    PG_URL: PostgreSQL 连接 URL（默认 postgresql://odysseia:changeme@localhost:5432/odysseia）
"""

import asyncio
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import asyncpg
import sqlalchemy as sa

# 确保 src/ 在 Python 路径中（本地运行时需要）
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402
import models  # noqa: E402, F401 — 注册所有表到 SQLModel.metadata
from shared.text_utils import build_search_vector_text  # noqa: E402

# ── 配置 ────────────────────────────────────────────

SQLITE_PATH = os.environ.get("SQLITE_PATH", "data/database.db")
PG_URL = os.environ.get(
    "PG_URL", "postgresql://odysseia:changeme@localhost:5432/odysseia"
)
BATCH_SIZE = 500

# ── 辅助函数 ────────────────────────────────────────


def _build_search_tokens(title: str | None, excerpt: str | None) -> str | None:
    """复用在线索引的规范化和分词规则，避免迁移生成旧规则向量。"""
    return build_search_vector_text(title, excerpt)


def _convert_sqlite_value(val, col_name: str, col_type: str = ""):
    """将 SQLite 值转换为 PostgreSQL 兼容类型。"""
    if val is None:
        return None
    # JSON 列：保持为 JSON 字符串，PG 会自动解析
    if col_type == "JSON" or col_name in (
        "thumbnail_urls",
        "preferred_channels",
        "include_authors",
        "exclude_authors",
        "include_tags",
        "exclude_tags",
        "exclude_keyword_exemption_markers",
    ):
        if isinstance(val, str):
            return val if val else "[]"
        import json

        return json.dumps(val, ensure_ascii=False)
    # SQLite 的布尔值是 0/1，PG 需要 True/False
    if col_type in ("BOOLEAN", "BOOL") or col_name in (
        "show_flag",
        "is_public",
        "is_anonymous",
        "is_default",
        "is_tournament",
    ):
        if isinstance(val, int):
            return bool(val)
        if isinstance(val, str):
            return val.lower() in ("1", "true", "yes")
    # SQLite 时间列存储为字符串，PG 需要 datetime 对象
    if col_type in ("DATETIME", "TIMESTAMP") and isinstance(val, str):
        # 尝试多种 SQLite 日期格式
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        # 如果无法解析，返回原始字符串（PG 可能能自动转换）
        return val
    return val


# ── 表迁移顺序（按外键依赖） ─────────────────────────

# PG 表名：SQLite 表名映射（生产环境 SQLite 历史遗留命名不一致）
SQLITE_TABLE_MAP = {
    "thread_tag_link": "threadtaglink",
    "user_search_preferences": "usersearchpreferences",
}

TABLE_ORDER = [
    "author",
    "tag",
    "bot_config",
    "thread",
    "thread_tag_link",
    "tag_vote",
    "thread_follow",
    "user_search_preferences",
    "user_update_preference",
    "mutex_tag_group",
    "mutex_tag_rule",
    "banner_application",
    "banner_carousel",
    "banner_waitlist",
    "user_collection",
    "booklist",
    "booklist_item",
]

# 需要用 rjieba 填充 search_vector 的表
SEARCH_VECTOR_TABLE = "thread"


def _sqlite_name(pg_table: str) -> str:
    """获取 PG 表名对应的 SQLite 表名（处理历史遗留命名不一致）。"""
    return SQLITE_TABLE_MAP.get(pg_table, pg_table)


async def main():
    print(f"SQLite 源: {SQLITE_PATH}")
    print(f"PostgreSQL 目标: {PG_URL}")

    # ── 0. 建表（若不存在）──
    print("创建表结构...")
    # PG_URL 是同步 URL (postgresql://)，转为异步 (postgresql+asyncpg://)
    async_db_url = PG_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    _engine = create_async_engine(async_db_url)
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    await _engine.dispose()
    print("表结构就绪\n")

    # ── 0.5. 修正列类型（SQLModel create_all 对 BigInteger/Boolean 映射不准）──
    print("修正列类型 (INTEGER→BIGINT, INTEGER→BOOLEAN)...")
    _fix_engine = create_async_engine(async_db_url)
    async with _fix_engine.begin() as conn:
        # INTEGER ID 列 → BIGINT（Discord Snowflake 是 64 位）
        await conn.execute(
            sa.text("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN
                        SELECT table_name, column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND data_type = 'integer'
                          AND (column_name LIKE '%_id' OR column_name = 'id'
                               OR column_name = 'guild_id')
                    LOOP
                        EXECUTE format(
                            'ALTER TABLE %I ALTER COLUMN %I TYPE BIGINT',
                            r.table_name, r.column_name
                        );
                    END LOOP;
                END $$;
            """)
        )
        # Boolean 列：INTEGER → BOOLEAN
        await conn.execute(
            sa.text("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN
                        SELECT table_name, column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND data_type = 'integer'
                          AND column_name IN (
                              'show_flag', 'is_public', 'is_anonymous',
                              'is_default', 'is_tournament', 'enabled'
                          )
                    LOOP
                        EXECUTE format(
                            'ALTER TABLE %I ALTER COLUMN %I TYPE BOOLEAN '
                            'USING (CASE WHEN %I = 0 THEN false ELSE true END)',
                            r.table_name, r.column_name, r.column_name
                        );
                    END LOOP;
                END $$;
            """)
        )
    await _fix_engine.dispose()
    print("列类型修正完成\n")

    # ── 1. 连接数据库 ──
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = await asyncpg.connect(PG_URL)

    try:
        # ── 2. 检查 SQLite 中实际存在的表 ──
        sqlite_tables = {
            row[0]
            for row in sqlite_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = [t for t in TABLE_ORDER if _sqlite_name(t) not in sqlite_tables]
        if missing:
            print(f"SQLite 中不存在的表（将跳过）: {', '.join(missing)}")

        for table in TABLE_ORDER:
            sq_name = _sqlite_name(table)
            if sq_name not in sqlite_tables:
                print(f"  SQLite.{sq_name}: 不存在，跳过")
                continue
            count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {sq_name}").fetchone()[0]
            print(f"  SQLite.{sq_name}: {count} 行")

        # ── 3. 迁移每张表 ──
        for table in TABLE_ORDER:
            sq_name = _sqlite_name(table)
            if sq_name not in sqlite_tables:
                print(f"\n迁移表: {table} ← SQLite.{sq_name} 不存在，跳过")
                continue
            print(f"\n迁移表: {table} ← SQLite.{sq_name}")

            # 获取列名和类型
            pragma = sqlite_conn.execute(f"PRAGMA table_info({sq_name})").fetchall()
            columns = [row["name"] for row in pragma]
            col_types = {row["name"]: row["type"] for row in pragma}
            col_list = ", ".join(columns)
            placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))

            # 读取数据
            rows = sqlite_conn.execute(f"SELECT {col_list} FROM {sq_name}").fetchall()

            if not rows:
                print("  空表，跳过")
                continue

            # 批量插入 PG
            total = len(rows)
            for offset in range(0, total, BATCH_SIZE):
                batch = rows[offset : offset + BATCH_SIZE]
                pg_batch = []
                for row in batch:
                    converted = tuple(
                        _convert_sqlite_value(row[col], col, col_types.get(col, ""))
                        for col in columns
                    )
                    pg_batch.append(converted)

                await pg_conn.executemany(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                    f"ON CONFLICT DO NOTHING",
                    pg_batch,
                )
                print(f"  已迁移 {min(offset + BATCH_SIZE, total)}/{total}")

            # 验证行数
            pg_count = await pg_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"  PG.{table}: {pg_count} 行")

        # ── 4. 填充 search_vector ──
        print("\n填充 search_vector...")
        thread_rows = await pg_conn.fetch(
            "SELECT id, thread_id, title, first_message_excerpt FROM thread"
        )
        updated = 0
        for row in thread_rows:
            tokens_text = _build_search_tokens(
                row["title"], row["first_message_excerpt"]
            )
            if tokens_text:
                await pg_conn.execute(
                    "UPDATE thread SET search_vector = to_tsvector('simple', $1) WHERE id = $2",
                    tokens_text,
                    row["id"],
                )
                updated += 1
                if updated % 100 == 0:
                    print(f"  已更新 {updated} 行 search_vector")
        print(f"search_vector 更新完成: {updated}/{len(thread_rows)}")

        # ── 5. 创建 GIN 索引 ──
        print("\n创建 GIN 索引...")
        await pg_conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_thread_search_vector "
            "ON thread USING GIN (search_vector)"
        )

        # ── 6. 重置序列 ──
        print("\n重置序列...")
        for table in TABLE_ORDER:
            try:
                await pg_conn.execute(
                    f"SELECT setval('{table}_id_seq', "
                    f"(SELECT COALESCE(MAX(id), 0) FROM {table}))"
                )
            except Exception as e:
                print(f"  ⚠ 序列重置失败 {table}_id_seq: {e}")

        print("\n* Migration completed! *")

    finally:
        sqlite_conn.close()
        await pg_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
