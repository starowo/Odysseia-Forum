from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config, pool, event
from alembic import context
from sqlmodel import SQLModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from models import *  # noqa: F403
from shared.fts5_tokenizer import register_jieba_tokenizer


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # 为 Alembic 连接注册分词器
    @event.listens_for(connectable, "connect")
    def on_connect(dbapi_connection, connection_record):
        """为 Alembic 的每个 SQLite 连接注册 jieba 分词器。"""
        try:
            dbapi_connection.execute("PRAGMA journal_mode=WAL")
            register_jieba_tokenizer(dbapi_connection)
        except Exception as e:
            print(f"为 Alembic 连接注册分词器失败: {e}")
            raise

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
