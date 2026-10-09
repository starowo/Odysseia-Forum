import os

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

# 确保表被导入，以便 SQLModel.metadata.create_all 能够工作

# 从环境变量读取数据库 URL（Docker 部署时由 docker-compose 注入），
# 本地开发时回退到默认的 PostgreSQL URL。
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://odysseia:changeme@localhost:5432/odysseia",
)


def _read_pool_int(name: str, default: int, *, minimum: int) -> int:
    """读取并校验数据库连接池整数配置。"""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值: {raw_value!r}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} 必须大于等于 {minimum}，当前值: {value}")
    return value


DB_POOL_SIZE = _read_pool_int("DB_POOL_SIZE", 5, minimum=1)
DB_MAX_OVERFLOW = _read_pool_int("DB_MAX_OVERFLOW", 8, minimum=0)
DB_POOL_TIMEOUT = _read_pool_int("DB_POOL_TIMEOUT", 30, minimum=1)

async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=True,
)


def is_deadlock_error(exc: Exception) -> bool:
    """检测是否是 PostgreSQL 死锁错误 (sqlstate 40P01)。"""
    orig = getattr(exc, "orig", None)
    if orig is None:
        return False
    return getattr(orig, "sqlstate", None) == "40P01" or "deadlock" in str(orig).lower()


async def init_db():
    """创建所有表（如果尚不存在）并建立全文搜索索引。"""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def init_db_for_test(engine_instance: AsyncEngine):
    """为测试环境初始化数据库（创建表及索引）。"""
    async with engine_instance.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db():
    """
    关闭数据库引擎，释放连接池。
    """
    print("正在关闭数据库连接池...")
    await async_engine.dispose()
    print("数据库连接池已关闭。")
