import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Column, Integer, MetaData, SQLModel, Table, Text, text

from shared.fts5_tokenizer import register_jieba_tokenizer

# 确保表被导入，以便 SQLModel.metadata.create_all 能够工作

DB_PATH = "data/database.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

async_engine = create_async_engine(DATABASE_URL, echo=False)

metadata_obj = MetaData()
thread_fts_table = Table(
    "thread_fts",
    metadata_obj,
    Column("rowid", Integer, primary_key=True),
    Column("title", Text),
    Column("first_message_excerpt", Text),
    Column("thread_fts", Text),
)


@event.listens_for(async_engine.sync_engine, "connect")
def _setup_tokenizer_on_connect(dbapi_connection, connection_record):
    """
    为每个新的 SQLite 连接注册 jieba 分词器。
    执行双层解包以从 SQLAlchemy 异步适配器中获取标准连接。
    """
    try:
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        # dbapi_connection 是 SQLAlchemy 的异步包装器 (AsyncAdapt_...)
        # 访问其 ._connection 属性，获取原始的 aiosqlite.Connection
        aiosqlite_conn = dbapi_connection._connection

        # 访问 aiosqlite.Connection 的内部 ._conn 属性，获取最终的标准 sqlite3.Connection
        underlying_sqlite3_conn = aiosqlite_conn._conn

        register_jieba_tokenizer(underlying_sqlite3_conn)

    except Exception as e:
        print(f"在新连接上注册分词器失败，解包过程可能出现问题: {e}")
        raise


AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)


async def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    async with async_engine.begin() as conn:
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
                AFTER UPDATE ON thread
                WHEN
                    new.title IS NOT old.title OR
                    new.first_message_excerpt IS NOT old.first_message_excerpt
                BEGIN
                    INSERT INTO thread_fts(thread_fts, rowid, title, first_message_excerpt)
                    VALUES ('delete', old.id, old.title, old.first_message_excerpt);
                    INSERT INTO thread_fts(rowid, title, first_message_excerpt)
                    VALUES (new.id, new.title, new.first_message_excerpt);
                END;
                """
            )
        )


async def init_db_for_test(engine_instance: AsyncEngine):
    @event.listens_for(engine_instance.sync_engine, "connect")
    def on_connect(dbapi_conn, connection_record):
        register_jieba_tokenizer(dbapi_conn)

    async with engine_instance.begin() as conn:
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
                AFTER UPDATE ON thread
                WHEN
                    new.title IS NOT old.title OR
                    new.first_message_excerpt IS NOT old.first_message_excerpt
                BEGIN
                    INSERT INTO thread_fts(thread_fts, rowid, title, first_message_excerpt)
                    VALUES ('delete', old.id, old.title, old.first_message_excerpt);
                    INSERT INTO thread_fts(rowid, title, first_message_excerpt)
                    VALUES (new.id, new.title, new.first_message_excerpt);
                END;
                """
            )
        )


async def close_db():
    """
    关闭数据库引擎，释放连接池。
    """
    print("正在关闭数据库连接池...")
    await async_engine.dispose()
    print("数据库连接池已关闭。")
