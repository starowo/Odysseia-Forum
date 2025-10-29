# tests/test_search_repository.py

import pytest
import pytest_asyncio
from typing import AsyncGenerator, List, Set
from datetime import datetime

from sqlalchemy.pool import StaticPool
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel, text, delete

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from shared.fts5_tokenizer import register_jieba_tokenizer
from shared.models.thread import Thread
from search.search_service import SearchService
from search.qo.thread_search import ThreadSearchQuery
from core.tag_service import TagService

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="module")
async def db_session_factory() -> AsyncGenerator[
    async_sessionmaker[AsyncSession], None
]:
    """
    创建一个模块级别的数据库引擎和会话工厂。
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_conn, connection_record):
        try:
            aiosqlite_conn = dbapi_conn._connection
            underlying_sqlite3_conn = aiosqlite_conn._conn
            register_jieba_tokenizer(underlying_sqlite3_conn)
        except Exception as e:
            print(f"在新连接上注册分词器失败: {e}")
            raise

    # 数据库初始化逻辑（包括FTS表和触发器）
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS thread_fts USING fts5(
                    title,
                    first_message_excerpt,
                    content='thread',
                    content_rowid='id',
                    tokenize = 'jieba'
                );
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS thread_after_insert
                AFTER INSERT ON thread BEGIN
                    INSERT INTO thread_fts(rowid, title, first_message_excerpt)
                    VALUES (new.id, new.title, new.first_message_excerpt);
                END;
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS thread_after_delete
                AFTER DELETE ON thread BEGIN
                    INSERT INTO thread_fts(thread_fts, rowid, title, first_message_excerpt)
                    VALUES ('delete', old.id, old.title, old.first_message_excerpt);
                END;
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS thread_after_update
                AFTER UPDATE ON thread BEGIN
                    INSERT INTO thread_fts(thread_fts, rowid, title, first_message_excerpt)
                    VALUES ('delete', old.id, old.title, old.first_message_excerpt);
                    INSERT INTO thread_fts(rowid, title, first_message_excerpt)
                    VALUES (new.id, new.title, new.first_message_excerpt);
                END;
                """
            )
        )

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def seeded_db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    提供一个填充了测试数据的数据库会话。
    使用 function 级别确保每个测试用例都在一个干净的数据环境中运行。
    """
    async with db_session_factory() as session:
        # 测试数据
        threads_to_create = [
            Thread(
                channel_id=1,
                thread_id=101,
                title="关于百合破坏的讨论",
                author_id=1,
                created_at=datetime.now(),
            ),
            Thread(
                channel_id=1,
                thread_id=102,
                title="🈲百合破坏",
                author_id=2,
                created_at=datetime.now(),
            ),
            Thread(
                channel_id=1,
                thread_id=103,
                title="小说推荐",
                author_id=3,
                created_at=datetime.now(),
            ),
            Thread(
                channel_id=1,
                thread_id=104,
                title="禁：请勿讨论百合破坏话题",
                author_id=4,
                created_at=datetime.now(),
            ),
            Thread(
                channel_id=1,
                thread_id=105,
                title="纯爱小说分享",
                author_id=5,
                created_at=datetime.now(),
            ),
        ]
        session.add_all(threads_to_create)
        await session.commit()

        yield session

        # 在每个测试结束后清理数据，确保测试之间的独立性
        await session.execute(delete(Thread))
        await session.commit()


# --- 参数化测试 ---
@pytest.mark.parametrize(
    "test_id, exclude_keywords, exemption_markers, expected_count, expected_present, expected_absent",
    [
        (
            "1_full_word_with_exemption",
            "百合破坏",
            ["禁", "🈲"],
            4,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论"},
        ),
        (
            "2_prefix_with_exemption",
            "百合破",
            ["禁", "🈲"],
            4,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论"},
        ),
        (
            "3_general_prefix_with_exemption",
            "百合",
            ["禁", "🈲"],
            4,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论"},
        ),
        (
            "4_full_word_no_exemption",
            "百合破坏",
            [],
            2,
            {"小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论", "🈲百合破坏", "禁：请勿讨论百合破坏话题"},
        ),
        (
            "5_prefix_no_exemption",
            "百合破",
            [],
            2,
            {"小说推荐", "纯爱小说分享"},
            {"关于百合破坏的讨论", "🈲百合破坏", "禁：请勿讨论百合破坏话题"},
        ),
        (
            "6_multiple_keywords_or_logic",
            "百合破坏 小说",
            [],
            0,
            set(),
            {
                "关于百合破坏的讨论",
                "🈲百合破坏",
                "禁：请勿讨论百合破坏话题",
                "小说推荐",
                "纯爱小说分享",
            },
        ),
        (
            "7_multiple_keywords_with_exemption",
            "百合破坏 纯爱",
            ["禁", "🈲"],
            3,
            {"🈲百合破坏", "禁：请勿讨论百合破坏话题", "小说推荐"},
            {"关于百合破坏的讨论", "纯爱小说分享"},
        ),
    ],
)
@pytest.mark.asyncio
async def test_search_exclusion_scenarios(
    seeded_db_session: AsyncSession,
    db_session_factory: async_sessionmaker[AsyncSession],
    test_id: str,
    exclude_keywords: str,
    exemption_markers: List[str],
    expected_count: int,
    expected_present: Set[str],
    expected_absent: Set[str],
):
    """
    对反选关键词的各种场景进行参数化测试。
    """
    # 1. 准备
    tag_service = TagService(session_factory=db_session_factory)
    await tag_service.build_cache()
    repo = SearchService(session=seeded_db_session, tag_service=tag_service)

    # 2. 构建查询
    query = ThreadSearchQuery(
        exclude_keywords=exclude_keywords,
        exclude_keyword_exemption_markers=exemption_markers,
    )

    # 3. 执行搜索
    threads, total_threads = await repo.search_threads_with_count(
        query=query,
        offset=0,
        limit=10,
        total_display_count=1000,
        exploration_factor=1.414,
        strength_weight=10.0,
    )

    # 4. 断言结果
    returned_titles = {t.title for t in threads}

    print(f"--- 运行测试: {test_id} ---")
    print(f"排除关键词: '{exclude_keywords}'")
    print(f"返回的标题: {returned_titles}")
    print(f"预期数量: {expected_count}, 实际: {total_threads}")
    print(f"预期存在: {expected_present}")
    print(f"预期不存在: {expected_absent}")

    assert total_threads == expected_count, f"测试 '{test_id}' 失败：总数不匹配"
    assert returned_titles.issuperset(expected_present), (
        f"测试 '{test_id}' 失败：部分预期结果缺失"
    )
    assert not returned_titles.intersection(expected_absent), (
        f"测试 '{test_id}' 失败：返回了不应出现的结果"
    )
