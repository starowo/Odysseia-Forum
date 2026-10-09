"""PostgreSQL 数据库迁移脚本。

1. 检查数据库可达
2. 可选 pg_dump 备份（BACKUP_BEFORE_MIGRATE=1）
3. 检查并输出当前 Alembic 版本
4. 执行 alembic upgrade head
5. 若 data/follow_bot.db 存在，迁移旧收藏数据到 booklist_item
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"


# ── 终端输出辅助 ──────────────────────────────────────────


def print_info(msg: str) -> None:
    print(f"\033[94m[INFO] {msg}\033[0m")


def print_success(msg: str) -> None:
    print(f"\033[92m[OK] {msg}\033[0m")


def print_warning(msg: str) -> None:
    print(f"\033[93m[WARN] {msg}\033[0m")


def print_error(msg: str) -> None:
    print(f"\033[91m[ERR] {msg}\033[0m")


# ── PostgreSQL 工具 ────────────────────────────────────────


def _pg_components(db_url: str) -> tuple[str, str, str, str, str]:
    """从 DATABASE_URL 解析 (host, port, dbname, user, password)。"""
    u = urlparse(db_url)
    return (
        u.hostname or "localhost",
        str(u.port or 5432),
        u.path.lstrip("/"),
        u.username or "",
        u.password or "",
    )


def check_db_reachable(db_url: str) -> bool:
    """用 pg_isready 检查数据库可达。"""
    host, port, dbname, user, _ = _pg_components(db_url)
    try:
        subprocess.run(
            [
                "pg_isready",
                "-h",
                host,
                "-p",
                port,
                "-d",
                dbname,
                "-U",
                user,
                "-t",
                "10",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def backup_db(db_url: str) -> Path | None:
    """用 pg_dump 备份数据库，返回备份文件路径。"""
    host, port, dbname, user, password = _pg_components(db_url)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATA_DIR / f"pre_migrate_backup_{ts}.sql"
    try:
        subprocess.run(
            [
                "pg_dump",
                "-h",
                host,
                "-p",
                port,
                "-d",
                dbname,
                "-U",
                user,
                "--no-owner",
                "--no-acl",
                "-f",
                str(backup_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PGPASSWORD": password},
        )
        return backup_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_warning(f"pg_dump 备份失败: {e}")
        return None


# ── Alembic 迁移 ───────────────────────────────────────────


def get_current_database_version() -> str:
    """获取当前数据库的 Alembic 版本。"""
    try:
        result = subprocess.run(
            ["alembic", "current"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.stdout.strip()
    except FileNotFoundError:
        print_error("alembic 命令未找到，请确认依赖已安装")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_error("获取当前数据库版本失败")
        print(e.stderr)
        sys.exit(1)


def run_alembic_migration() -> None:
    """执行 alembic upgrade head。"""
    print_info("执行 alembic upgrade head ...")
    print_warning("请勿中断此过程。")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(result.stdout)
        print_success("Alembic 迁移完成")
    except FileNotFoundError:
        print_error("alembic 命令未找到，请确认依赖已安装")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_error("Alembic 迁移失败")
        print(e.stderr)
        sys.exit(1)

    # 输出迁移后版本
    print_info(f"迁移后数据库版本: {get_current_database_version()}")


# ── 旧收藏数据迁移（SQLite follow_bot.db → PostgreSQL booklist_item） ──


def migrate_favorites_from_follow_bot() -> None:
    """将旧 follow_bot.db 的 thread_favorites 迁移到当前系统的默认书单。

    仅当 data/follow_bot.db 存在时执行。使用 sqlite3 直接读取旧库，
    写入当前 PostgreSQL 数据库（通过 DATABASE_URL）。
    """
    import sqlite3

    import psycopg2
    import psycopg2.extras

    old_db_path = DATA_DIR / "follow_bot.db"
    if not old_db_path.exists():
        print_info("未找到 follow_bot.db，跳过旧收藏数据迁移。")
        return

    print_info("=" * 50)
    print_info("检测到 follow_bot.db，开始迁移旧收藏数据...")

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print_warning("DATABASE_URL 未设置，跳过旧收藏迁移")
        return

    # 同步 PostgreSQL 连接
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    batch_size = 100
    total_attempted = 0
    total_migrated = 0
    old_conn = None
    pg_conn = None

    try:
        old_conn = sqlite3.connect(str(old_db_path))
        old_cursor = old_conn.cursor()

        pg_conn = psycopg2.connect(sync_url)
        pg_cursor = pg_conn.cursor()

        # 查询旧库中所有收藏用户 ID
        old_cursor.execute("SELECT DISTINCT user_id FROM thread_favorites")
        old_user_ids = [row[0] for row in old_cursor.fetchall()]
        if not old_user_ids:
            print_info("旧数据库中没有收藏记录，跳过。")
            return
        print_info(f"旧库中共 {len(old_user_ids)} 个用户有收藏记录。")

        # 查询这些用户在当前库中的默认书单
        pg_cursor.execute(
            "SELECT id, owner_id FROM booklist WHERE owner_id = ANY(%s) AND is_default = true",
            (old_user_ids,),
        )
        existing_booklists = {row[1]: row[0] for row in pg_cursor.fetchall()}
        print_info(f"其中 {len(existing_booklists)} 个用户已有默认书单。")

        # 为没有默认书单的用户创建
        users_without_booklist = [
            uid for uid in old_user_ids if uid not in existing_booklists
        ]
        if users_without_booklist:
            now = datetime.now()
            psycopg2.extras.execute_values(
                pg_cursor,
                "INSERT INTO booklist (owner_id, title, description, is_public,"
                " is_default, default_sort_method, default_sort_order, item_count, collection_count,"
                " view_count, created_at, updated_at)"
                " VALUES %s RETURNING id, owner_id",
                [
                    (
                        uid,
                        "默认收藏",
                        "默认收藏夹",
                        False,
                        True,
                        "join_time",
                        "desc",
                        0,
                        0,
                        0,
                        now,
                        now,
                    )
                    for uid in users_without_booklist
                ],
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            )
            for row in pg_cursor.fetchall():
                existing_booklists[row[1]] = row[0]
            pg_conn.commit()
            print_success(f"为 {len(users_without_booklist)} 个用户创建了默认书单。")

        # 分批读取旧收藏数据
        old_cursor.execute(
            "SELECT user_id, thread_id, added_at FROM thread_favorites"
            " ORDER BY user_id, added_at"
        )

        booklist_max_order: dict[int, int] = {}

        while True:
            batch = old_cursor.fetchmany(batch_size)
            if not batch:
                break

            grouped: dict = {}
            for user_id, thread_id, added_at in batch:
                grouped.setdefault(user_id, []).append((thread_id, added_at))

            for user_id, items in grouped.items():
                booklist_id = existing_booklists.get(user_id)
                if booklist_id is None:
                    total_attempted += len(items)
                    continue

                thread_ids = [item[0] for item in items]

                # 去重
                pg_cursor.execute(
                    "SELECT thread_id FROM booklist_item"
                    " WHERE booklist_id = %s AND thread_id = ANY(%s)",
                    (booklist_id, thread_ids),
                )
                existing_thread_ids = set(row[0] for row in pg_cursor.fetchall())

                new_items = [
                    item for item in items if item[0] not in existing_thread_ids
                ]
                total_attempted += len(items)

                if new_items:
                    if booklist_id not in booklist_max_order:
                        pg_cursor.execute(
                            "SELECT COALESCE(MAX(display_order), 0) FROM booklist_item"
                            " WHERE booklist_id = %s",
                            (booklist_id,),
                        )
                        row = pg_cursor.fetchone()
                        booklist_max_order[booklist_id] = row[0] if row else 0

                    insert_data = []
                    for _, (thread_id, added_at) in enumerate(new_items):
                        booklist_max_order[booklist_id] += 1
                        insert_data.append(
                            (
                                booklist_id,
                                thread_id,
                                user_id,
                                booklist_max_order[booklist_id],
                                added_at,
                                added_at,
                            )
                        )

                    psycopg2.extras.execute_values(
                        pg_cursor,
                        "INSERT INTO booklist_item"
                        " (booklist_id, thread_id, owner_id, display_order,"
                        " created_at, updated_at)"
                        " VALUES %s",
                        insert_data,
                        template="(%s, %s, %s, %s, %s, %s)",
                    )
                    total_migrated += len(new_items)

                    pg_cursor.execute(
                        "UPDATE booklist SET item_count = item_count + %s WHERE id = %s",
                        (len(new_items), booklist_id),
                    )

            pg_conn.commit()

        total_ignored = total_attempted - total_migrated
        print_success(
            f"成功迁移 {total_migrated} 条收藏记录（忽略 {total_ignored} 条重复）。"
        )

        # 更新帖子收藏计数
        try:
            old_cursor.execute(
                "SELECT thread_id, COUNT(DISTINCT user_id) FROM thread_favorites"
                " GROUP BY thread_id"
            )
            collection_counts = old_cursor.fetchall()

            if collection_counts:
                psycopg2.extras.execute_values(
                    pg_cursor,
                    "UPDATE thread SET collection_count = collection_count + data.v"
                    " FROM (VALUES %s) AS data(tid, v)"
                    " WHERE thread.thread_id = data.tid",
                    collection_counts,
                    template="(%s, %s)",
                )
                pg_conn.commit()
                print_success(f"更新了 {len(collection_counts)} 个帖子的收藏计数。")
        except Exception as e:
            print_error(f"更新收藏计数出错: {e}")
            pg_conn.rollback()

    except Exception as e:
        if pg_conn:
            pg_conn.rollback()
        print_error(f"迁移旧收藏数据时出错: {e}")
        print_warning("旧收藏数据迁移失败，但不影响 Alembic 迁移结果。")
    finally:
        if old_conn:
            old_conn.close()
        if pg_conn:
            pg_conn.close()

    # 迁移完成后删除旧数据库文件
    try:
        old_db_path.unlink()
        print_success(f"已删除 {old_db_path.name}。")
    except Exception as e:
        print_error(f"删除 {old_db_path.name} 时出错: {e}")

    print_info("旧收藏数据迁移结束。")


# ── main ───────────────────────────────────────────────────


def main() -> None:
    print_info("=" * 50)
    print_info("  PostgreSQL 数据库迁移脚本")
    print_info("=" * 50)

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print_error("DATABASE_URL 环境变量未设置")
        sys.exit(1)

    # pg_isready / pg_dump 需要同步驱动 URL
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    # 检查数据库可达
    if not check_db_reachable(sync_url):
        print_error("数据库不可达，请检查 DATABASE_URL 和网络连接")
        sys.exit(1)
    print_success("数据库连接正常")

    # 可选 pg_dump 备份
    if os.environ.get("BACKUP_BEFORE_MIGRATE") == "1":
        print_info("正在备份数据库...")
        backup_path = backup_db(sync_url)
        if backup_path:
            print_success(f"备份完成: {backup_path}")

    # 迁移前确认当前数据库版本
    current_version = get_current_database_version()
    if not current_version:
        print_error("当前数据库没有 Alembic 版本号，已中断迁移。")
        print_warning("请人工判断数据库版本，切换到正确版本后重试。")
        sys.exit(1)
    print_info(f"当前数据库版本: {current_version}")

    # Alembic 迁移
    run_alembic_migration()

    # 旧收藏数据迁移（follow_bot.db）
    migrate_favorites_from_follow_bot()

    print_info("=" * 50)
    print_success("所有操作已完成，可以启动服务。")
    print_info("=" * 50)


if __name__ == "__main__":
    main()
