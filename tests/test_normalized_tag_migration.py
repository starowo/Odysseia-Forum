# ruff: noqa: F811
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from test_custom_tag_governance import setup_tags  # noqa: F401


@pytest.mark.asyncio
async def test_abyss_flag_migration_defaults_backfills_and_downgrades(setup_tags):
    """迁移为新旧 TAG 写入 false 默认值，并可安全降级移除字段。"""
    factory, _, _ = setup_tags
    schema = "test_abyss_flag_migration_" + uuid4().hex
    path = Path(__file__).parents[1] / "alembic/versions/add_abyss_tag_flag.py"
    spec = importlib.util.spec_from_file_location("abyss_flag_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    async with factory() as session, session.begin():
        await session.execute(text(f'CREATE SCHEMA "{schema}"'))
        await session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        await session.execute(
            text("CREATE TABLE tag (id BIGINT PRIMARY KEY, name VARCHAR NOT NULL)")
        )
        await session.execute(text("INSERT INTO tag VALUES (1, '旧标签')"))
        connection = await session.connection()

        def upgrade(conn):
            """在隔离 schema 内执行升级。"""
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()

        def downgrade(conn):
            """在隔离 schema 内执行降级。"""
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()

        await connection.run_sync(upgrade)
        await session.execute(text("INSERT INTO tag (id, name) VALUES (2, '新标签')"))
        assert (
            await session.execute(text("SELECT id, is_abyss FROM tag ORDER BY id"))
        ).all() == [(1, False), (2, False)]

        await session.execute(text("UPDATE tag SET is_abyss = true WHERE id = 2"))
        assert (
            await session.execute(text("SELECT is_abyss FROM tag WHERE id = 2"))
        ).scalar_one() is True

        await connection.run_sync(downgrade)
        assert (
            await session.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema=:schema AND table_name='tag' "
                    "AND column_name='is_abyss'"
                ),
                {"schema": schema},
            )
        ).scalar_one() == 0
        await session.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


@pytest.mark.asyncio
@pytest.mark.parametrize("conflict", [False, True])
async def test_incremental_normalization_preserves_history(setup_tags, conflict):
    """增量迁移保留票和原始审计，冲突时整个归一事务可回滚。"""
    factory, _, _ = setup_tags
    schema = "test_normalization_migration_" + uuid4().hex
    async with factory() as session, session.begin():
        await session.execute(text(f'CREATE SCHEMA "{schema}"'))
        await session.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        connection = await session.connection()

        def migrate(conn, filename):
            """直接执行指定迁移，验证真实 PostgreSQL DDL 和数据变换。"""
            path = Path(__file__).parents[1] / "alembic/versions" / filename
            spec = importlib.util.spec_from_file_location("migration_under_test", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with Operations.context(MigrationContext.configure(conn)):
                module.upgrade()

        for sql in [
            "CREATE TABLE tag (id BIGINT PRIMARY KEY, name VARCHAR NOT NULL)",
            "CREATE TABLE thread (id INTEGER PRIMARY KEY, channel_id BIGINT NOT NULL)",
            "CREATE TABLE thread_tag_link (thread_id INTEGER, tag_id BIGINT)",
            "CREATE TABLE notification (id SERIAL PRIMARY KEY, thread_id BIGINT NOT NULL, event_type VARCHAR, CONSTRAINT ck_notification_event_type CHECK(event_type IN ('thread_update','author_new_thread')))",
            "CREATE TABLE tag_vote (id SERIAL PRIMARY KEY, vote INTEGER)",
            "INSERT INTO tag VALUES (9007199254740993,'同名'), (9007199254740994,'同名')",
            "INSERT INTO thread VALUES (1,20),(2,30)",
            "INSERT INTO thread_tag_link VALUES (1,9007199254740993),(2,9007199254740994)",
        ]:
            await session.execute(text(sql))
        await connection.run_sync(migrate, "add_custom_tag_governance.py")
        for sql in [
            "INSERT INTO tag(name,source,category) VALUES ('同名','custom',3)",
            "INSERT INTO tag_binding(target_type,target_id,tag_id,binding_source,upvotes,downvotes,created_at) VALUES ('booklist',1,9007199254740993,'local',1,0,CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),('booklist',1,9007199254740995,'local',0,0,CURRENT_TIMESTAMP AT TIME ZONE 'UTC')",
            "INSERT INTO tag_vote(binding_id,user_id,vote) SELECT id,99,1 FROM tag_binding WHERE target_type='booklist' AND tag_id=9007199254740993",
            "INSERT INTO tag_alias(tag_id,name) VALUES (9007199254740995,'Alias')",
            "INSERT INTO tag_proposal_block(target_type,target_id,tag_id,created_at) VALUES ('booklist',2,9007199254740995,CURRENT_TIMESTAMP AT TIME ZONE 'UTC')",
            "INSERT INTO tag_proposal(target_type,target_id,tag_id,applicant_id,owner_id,created_at,status,due_at) VALUES ('booklist',2,9007199254740995,3,1,CURRENT_TIMESTAMP AT TIME ZONE 'UTC','pending',CURRENT_TIMESTAMP AT TIME ZONE 'UTC')",
            "INSERT INTO tag_notification_task(proposal_id,kind,status,attempts,available_at) SELECT id,'proposal','pending',0,CURRENT_TIMESTAMP AT TIME ZONE 'UTC' FROM tag_proposal",
            "INSERT INTO operation_log(type,target_type,target_id,tag_id,created_at,detail) VALUES ('old.fact','thread',9007199254740999,9007199254740994,CURRENT_TIMESTAMP AT TIME ZONE 'UTC','{\"old\": true}')",
        ]:
            await session.execute(text(sql))
        if conflict:
            await session.execute(
                text(
                    "INSERT INTO tag_relation VALUES (9007199254740993,9007199254740994,'excludes')"
                )
            )
            with pytest.raises(Exception, match="self relation"):
                async with connection.begin_nested():
                    await connection.run_sync(migrate, "normalize_discord_tags.py")
            assert (
                await session.execute(
                    text("SELECT count(*) FROM tag WHERE deleted_at IS NULL")
                )
            ).scalar_one() == 3
            assert (
                await session.execute(text("SELECT to_regclass('discord_tag_source')"))
            ).scalar_one() is None
        else:
            await connection.run_sync(migrate, "normalize_discord_tags.py")
            assert (
                await session.execute(
                    text("SELECT count(*) FROM tag WHERE deleted_at IS NULL")
                )
            ).scalar_one() == 1
            assert (
                await session.execute(text("SELECT count(*) FROM discord_tag_source"))
            ).scalar_one() == 2
            assert (
                await session.execute(
                    text(
                        "SELECT count(*) FROM tag_binding WHERE ended_at IS NULL AND tag_id=9007199254740993"
                    )
                )
            ).scalar_one() == 3
            assert (
                await session.execute(
                    text(
                        "SELECT upvotes FROM tag_binding WHERE target_type='booklist' AND ended_at IS NULL"
                    )
                )
            ).scalar_one() == 1
            assert (
                await session.execute(text("SELECT count(*) FROM tag_vote"))
            ).scalar_one() == 1
            assert (
                await session.execute(text("SELECT tag_id FROM tag_alias"))
            ).scalar_one() == 9007199254740993
            assert (
                await session.execute(
                    text(
                        "SELECT count(*) FROM tag_proposal_block WHERE tag_id=9007199254740993"
                    )
                )
            ).scalar_one() == 1
            assert (
                await session.execute(text("SELECT status,reason FROM tag_proposal"))
            ).one() == ("failed", "tag_merged")
            assert (
                await session.execute(text("SELECT status FROM tag_notification_task"))
            ).scalar_one() == "cancelled"
        assert (
            await session.execute(text("SELECT count(*) FROM thread_tag_link"))
        ).scalar_one() == 2
        assert (
            await session.execute(
                text(
                    "SELECT target_id,tag_id,detail FROM operation_log WHERE type='old.fact'"
                )
            )
        ).one() == (9007199254740999, 9007199254740994, {"old": True})
        await session.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
