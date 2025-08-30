import asyncio
import aiosqlite
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 导入新数据库的模型
from shared.models.user_search_preferences import UserSearchPreferences
from shared.database import init_db as init_new_db

# 定义旧数据库和新数据库的路径
OLD_DB_PATH = "forum_search.db"
NEW_DB_PATH = "data/database.db"
NEW_DATABASE_URL = f"sqlite+aiosqlite:///{NEW_DB_PATH}"


def parse_author_list(authors_str: Optional[str]) -> list[int]:
    """将逗号分隔的作者ID字符串解析为整数列表。"""
    if not authors_str:
        return []
    return [int(x) for x in authors_str.split(",") if x.strip()]


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """将字符串转换为datetime对象，如果格式无效则返回None。"""
    if not date_str:
        return None
    try:
        # 假设日期格式为 YYYY-MM-DD
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


async def migrate_user_preferences():
    """执行用户偏好数据的迁移。"""
    print("开始迁移用户偏好设置...")

    # 1. 初始化新数据库，确保表已创建
    await init_new_db()

    # 2. 连接到新旧数据库
    new_engine = create_async_engine(NEW_DATABASE_URL, echo=False)

    async with aiosqlite.connect(OLD_DB_PATH) as old_db:
        old_db.row_factory = aiosqlite.Row

        # 3. 从旧数据库读取数据
        # 使用 LEFT JOIN 以确保即使某个用户没有搜索偏好，也能获取到他们的 results_per_page
        query = """
            SELECT
                p.user_id,
                p.results_per_page,
                sp.include_authors,
                sp.exclude_authors,
                sp.after_date,
                sp.before_date,
                sp.preview_image_mode
            FROM user_preferences p
            LEFT JOIN user_search_preferences sp ON p.user_id = sp.user_id
        """
        async with old_db.execute(query) as cursor:
            old_prefs = await cursor.fetchall()

        if not old_prefs:
            print("在旧数据库中没有找到用户偏好数据。")
            return

        print(f"从旧数据库中找到 {len(old_prefs)} 条用户偏好记录。")

        # 4. 转换数据并准备写入新数据库
        new_prefs_to_add = []
        for row in old_prefs:
            # 合并和转换数据
            new_pref = UserSearchPreferences(
                user_id=row["user_id"],
                results_per_page=row["results_per_page"] or 6,  # 提供默认值
                include_authors=parse_author_list(row["include_authors"]),
                exclude_authors=parse_author_list(row["exclude_authors"]),
                after_date=parse_date(row["after_date"]),
                before_date=parse_date(row["before_date"]),
                preview_image_mode=row["preview_image_mode"]
                or "thumbnail",  # 提供默认值
            )
            new_prefs_to_add.append(new_pref)

        # 5. 写入新数据库
        async with AsyncSession(new_engine) as session:
            print(f"正在向新数据库写入 {len(new_prefs_to_add)} 条记录...")
            session.add_all(new_prefs_to_add)
            await session.commit()
            print("写入完成。")

    print("用户偏好数据迁移成功！")


if __name__ == "__main__":
    # 检查旧数据库文件是否存在
    import os

    if not os.path.exists(OLD_DB_PATH):
        print(
            f"错误：旧数据库文件 '{OLD_DB_PATH}' 不存在。请将旧数据库文件放在正确的位置。"
        )
    else:
        asyncio.run(migrate_user_preferences())
