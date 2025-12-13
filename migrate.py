# migrate.py
import sqlite3
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# --- 配置 ---
# 使用 pathlib 确保跨平台路径兼容性
PROJECT_ROOT = Path(__file__).parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "database.db"
CACHE_PATH = DATA_DIR / "username_cache.json"
# --- 结束配置 ---


# 用于在终端输出彩色文本的辅助函数
def print_color(text, color_code):
    """在终端打印彩色文本"""
    print(f"\033[{color_code}m{text}\033[0m")


def print_info(message):
    print_color(f"ℹ️  {message}", "94")  # Blue


def print_success(message):
    print_color(f"✅ {message}", "92")  # Green


def print_warning(message):
    print_color(f"⚠️  {message}", "93")  # Yellow


def print_error(message):
    print_color(f"❌ {message}", "91")  # Red


def adapt_datetime(dt_obj):
    """将 datetime 对象转换为 'YYYY-MM-DD HH:MM:SS.ffffff' 格式的字符串，以匹配 SQLAlchemy 的默认格式。"""
    return dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")


def parse_iso_datetime_with_timezone(s):
    """解析带 '+00:00' 时区后缀的日期时间字符串"""
    # Python 3.11+ 的 fromisoformat可以直接处理 'Z' 和 '+00:00'
    # 为了兼容性，我们手动处理
    try:
        # 移除可能存在的时区信息，因为 sqlite3 会存储 naive datetime
        s_str = s.decode("utf-8")
        if "+" in s_str:
            return datetime.fromisoformat(s_str.split("+")[0])
        return datetime.fromisoformat(s_str)
    except (ValueError, TypeError):
        return None


def migrate_favorites_from_follow_bot():
    """如果存在旧的 follow_bot.db，则将其 thread_favorites 数据分批迁移到 user_collection"""
    old_db_path = DATA_DIR / "follow_bot.db"
    if not old_db_path.exists():
        print_info("未找到旧的收藏数据库 (follow_bot.db)，跳过数据迁移。")
        return

    print_info("=" * 50)
    print_info("检测到旧的收藏数据库，开始迁移数据...")

    batch_size = 100  # 每次处理 100 条记录
    total_migrated = 0
    total_ignored = 0
    old_conn = None
    main_conn = None

    try:
        # 注册自定义的转换器和适配器来处理 datetime 对象
        sqlite3.register_adapter(datetime, adapt_datetime)
        sqlite3.register_converter("timestamp", parse_iso_datetime_with_timezone)

        # 连接旧数据库和主数据库 (detect_types 会启用类型转换)
        old_conn = sqlite3.connect(
            old_db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        old_cursor = old_conn.cursor()

        main_conn = sqlite3.connect(DB_PATH)
        main_cursor = main_conn.cursor()

        # 开启事务
        main_cursor.execute("BEGIN TRANSACTION")

        # 从旧数据库读取数据
        old_cursor.execute("SELECT user_id, thread_id, added_at FROM thread_favorites")

        while True:
            # 分批获取数据
            favorites_batch = old_cursor.fetchmany(batch_size)
            if not favorites_batch:
                break  # 没有更多数据了

            # 准备批量插入
            insert_query = """
            INSERT OR IGNORE INTO user_collection (user_id, target_type, target_id, created_at)
            VALUES (?, ?, ?, ?)
            """
            # target_type=1 代表帖子
            data_to_insert = [
                (user_id, 1, thread_id, added_at)
                for user_id, thread_id, added_at in favorites_batch
            ]

            # 执行批量插入
            main_cursor.executemany(insert_query, data_to_insert)

            # 更新计数
            migrated_in_batch = main_cursor.rowcount
            total_migrated += migrated_in_batch
            total_ignored += len(data_to_insert) - migrated_in_batch

        # 提交事务
        main_conn.commit()
        print_success(
            f"成功迁移 {total_migrated} 条收藏记录 (忽略了 {total_ignored} 条重复记录)。"
        )

        # 更新帖子的收藏计数
        try:
            # 从旧数据库统计每个帖子的收藏数
            old_cursor.execute(
                "SELECT thread_id, COUNT(*) FROM thread_favorites GROUP BY thread_id"
            )
            collection_counts = old_cursor.fetchall()

            if not collection_counts:
                print_info("旧数据库中没有收藏记录，无需更新计数。")
            else:
                # 在主数据库中批量更新
                update_query = """
                UPDATE thread
                SET collection_count = collection_count + ?
                WHERE thread_id = ?
                """
                # 重新组织数据为 (count, thread_id) 的格式
                update_data = [(count, tid) for tid, count in collection_counts]

                main_cursor.executemany(update_query, update_data)
                main_conn.commit()
                print_success(f"成功更新了 {main_cursor.rowcount} 个帖子的收藏计数。")

        except Exception as e:
            print_error(f"更新帖子收藏计数时出错: {e}")
            if main_conn:
                main_conn.rollback()

    except Exception as e:
        if main_conn:
            main_conn.rollback()  # 如果发生错误，回滚事务
        print_error(f"从 follow_bot.db 迁移数据时发生错误: {e}")
        print_warning("数据迁移失败，但不会影响 Alembic 的迁移结果。")
    finally:
        # 关闭数据库连接
        if old_conn:
            old_conn.close()
        if main_conn:
            main_conn.close()

    # 迁移完成后删除旧数据库文件
    try:
        old_db_path.unlink()
        print_success(f"已成功删除旧的收藏数据库 '{old_db_path.name}'。")
    except Exception as e:
        print_error(f"删除旧的收藏数据库时出错: {e}")

    print_info("旧数据迁移流程结束。")


def main():
    """执行完整的数据库迁移流程"""
    print_info("=" * 50)
    print_info("=  数据库自动迁移脚本启动")
    print_info("=" * 50)

    # 备份数据库
    print_info(f"正在备份数据库 '{DB_PATH.name}'...")
    if not DB_PATH.exists():
        print_error(f"错误：数据库文件未找到于 '{DB_PATH}'。请确保文件存在。")
        sys.exit(1)

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{DB_PATH.stem}.backup_{timestamp}{DB_PATH.suffix}"
        backup_path = DATA_DIR / backup_filename

        shutil.copy2(DB_PATH, backup_path)  # copy2 会保留元数据
        print_success(f"数据库已成功备份到: '{backup_path}'")
    except Exception as e:
        print_error(f"备份数据库时发生错误: {e}")
        sys.exit(1)

    # 运行 Alembic 迁移
    print_info("准备执行 Alembic 数据库迁移...")
    print_warning("这将更新数据库结构。请勿中断此过程。")

    try:
        # 使用 subprocess.run 来执行命令，check=True 会在命令失败时抛出异常
        command = ["alembic", "upgrade", "head"]
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
        )

        # 打印 Alembic 的输出信息
        print("--- Alembic 输出开始 ---")
        print(result.stdout)
        print("--- Alembic 输出结束 ---")

        print_success("数据库迁移成功完成！")
    except FileNotFoundError:
        print_error("错误：'alembic' 命令未找到。")
        print_error("请确保 Alembic 已通过 uv 安装在项目的开发依赖中。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_error("Alembic 迁移过程中发生错误！")
        print_error("--- Alembic 错误输出开始 ---")
        print(e.stderr)
        print_error("--- Alembic 错误输出结束 ---")
        print_warning("数据库结构可能处于不一致状态。建议使用备份文件进行恢复。")
        sys.exit(1)
    except Exception as e:
        print_error(f"执行迁移时发生未知错误: {e}")
        sys.exit(1)

    # 从 follow_bot.db 迁移收藏数据
    migrate_favorites_from_follow_bot()

    try:
        # 使用标准库 sqlite3 连接数据库
        conn = sqlite3.connect(DB_PATH)
        conn.execute("VACUUM;")
        conn.close()
    except Exception as e:
        print_error(f"执行 VACUUM 时发生错误: {e}")
        print_warning("数据库结构已更新，但优化步骤失败。机器人仍可正常运行。")

    print_info("=" * 50)
    print_success(" 所有操作已成功完成！现在可以启动机器人了。")
    print_info("=" * 50)


if __name__ == "__main__":
    main()
