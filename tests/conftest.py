"""
共享的 pytest fixtures，供所有测试文件使用。

提供函数级别的 PostgreSQL 数据库引擎和会话工厂，
每个测试独立建表、独立清理。
"""

import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlmodel import SQLModel

import os
import sys
import re
from sqlalchemy import text

# 确保 src/ 在 Python 路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# 注册所有表到 SQLModel.metadata
import models  # noqa: E402, F401

from shared.redis_client import RedisManager  # noqa: E402

TEST_DATABASE_URL = os.environ.get(
    "TEST_DB_URL",
    "postgresql+asyncpg://odysseia:changeme@localhost:5432/odysseia_test",
)

TEST_REDIS_URL = os.environ.get(
    "TEST_REDIS_URL",
    "redis://:xunmeng123456%21@localhost:6379/0",
)


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    """初始化 Redis 客户端，测试结束后关闭。"""
    await RedisManager.init_redis(TEST_REDIS_URL)
    yield RedisManager.get_client()
    await RedisManager.close_redis()


@pytest_asyncio.fixture(scope="function")
async def db_session_factory(
    redis_client,  # noqa: ARG001 — 确保 Redis 已初始化
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """函数级别的 PostgreSQL 数据库引擎 + 会话工厂（每测试独立）。"""
    schema = os.environ.get("TEST_DB_SCHEMA")
    if schema and not re.fullmatch(r"test_[a-z0-9_]+", schema):
        raise ValueError("TEST_DB_SCHEMA 必须是 test_ 前缀的安全测试 schema")
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}} if schema else {},
    )

    async with engine.begin() as conn:
        if schema:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=True, class_=AsyncSession)
    yield factory

    # 清空所有表，确保每个测试独立
    async with engine.begin() as conn:
        if schema:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            for table in reversed(SQLModel.metadata.sorted_tables):
                await conn.execute(table.delete())

    await engine.dispose()
