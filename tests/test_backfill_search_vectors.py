"""历史回填的 PostgreSQL 事务、续跑和并发修改测试。"""

import asyncio
import copy
import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.search_vector_backfill_repository import SearchVectorBackfillRepository
from models import Booklist, Thread
from shared.text_utils import build_search_vector_text

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "backfill_search_vectors.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "backfill_search_vectors", SCRIPT_PATH
)
assert SCRIPT_SPEC and SCRIPT_SPEC.loader
backfill = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(backfill)


@pytest_asyncio.fixture
async def old_vectors_engine(db_session_factory):
    """在独立测试 schema 构造原文保留但索引过时的帖子和书单。"""
    engine = db_session_factory.kw["bind"]
    async with db_session_factory() as session:
        for index, (title, body) in enumerate(
            [("軟體", "滑鼠 記憶體"), ("寬頻", None), ("", None)], start=1
        ):
            session.add(
                Thread(
                    id=index,
                    thread_id=100 + index,
                    channel_id=1,
                    author_id=1,
                    title=title,
                    first_message_excerpt=body,
                    reaction_count=7,
                )
            )
            session.add(
                Booklist(
                    id=index,
                    owner_id=1,
                    title=title,
                    description=body,
                    item_count=9,
                    view_count=8,
                )
            )
        await session.commit()
    async with engine.begin() as connection:
        for table in ("thread", "booklist"):
            await connection.execute(
                text(
                    f"UPDATE {table} SET search_vector = to_tsvector('simple', 'legacy')"
                )
            )
    yield engine


async def snapshot(engine, table):
    """读取全部字段，用于断言回填只修改搜索向量。"""
    async with engine.connect() as connection:
        return list(
            (
                await connection.execute(
                    text(
                        f"SELECT row_to_json(target) FROM {table} AS target ORDER BY id"
                    )
                )
            ).scalars()
        )


async def assert_vectors_match_sources(engine, table):
    """使用 PostgreSQL 重算预期向量并核对每条原文。"""
    rows = await snapshot(engine, table)
    body_column = "first_message_excerpt" if table == "thread" else "description"
    async with engine.connect() as connection:
        for row in rows:
            tokens = build_search_vector_text(row["title"], row[body_column])
            result = await connection.execute(
                text("SELECT CAST(to_tsvector('simple', :tokens) AS text)"),
                {"tokens": tokens},
            )
            assert row["search_vector"] == result.scalar_one()


def arguments(tmp_path, table="all", batch_size=500, resume=False):
    """构造使用独立临时检查点的脚本参数。"""
    args = backfill.parse_args(
        [
            "--table",
            table,
            "--batch-size",
            str(batch_size),
            "--sleep",
            "0",
            "--checkpoint",
            str(tmp_path / "checkpoint.json"),
        ]
    )
    args.resume = resume
    return args


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["all", "thread", "booklist"])
async def test_backfill_only_vectors_and_safe_repeat(
    old_vectors_engine, tmp_path, table, capsys
):
    """所有业务字段及书单更新时间不变，支持完成续跑与新检查点重复处理。"""
    engine = old_vectors_engine
    before = {name: await snapshot(engine, name) for name in ("thread", "booklist")}
    args = arguments(tmp_path, table, batch_size=2)
    state = await backfill.run_backfill(engine, engine.url, args)
    selected = ("thread", "booklist") if table == "all" else (table,)
    for name in selected:
        assert state["tables"][name] == {
            "cursor": 3,
            "upper_bound": 3,
            "processed": 3,
            "deleted": 0,
        }
        await assert_vectors_match_sources(engine, name)
    after = {name: await snapshot(engine, name) for name in ("thread", "booklist")}
    for name in after:
        assert [
            {key: value for key, value in row.items() if key != "search_vector"}
            for row in after[name]
        ] == [
            {key: value for key, value in row.items() if key != "search_vector"}
            for row in before[name]
        ]
        if name not in selected:
            assert after[name] == before[name]
    checkpoint = args.checkpoint.read_text(encoding="utf8")
    assert engine.url.password not in checkpoint
    args.resume = True
    assert await backfill.run_backfill(engine, engine.url, args) == state
    args.resume = False
    args.checkpoint = tmp_path / "repeat.json"
    await backfill.run_backfill(engine, engine.url, args)
    for name in after:
        assert await snapshot(engine, name) == after[name]
    assert "回填完成，失败=0" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_interrupt_resume_retains_startup_limits(
    old_vectors_engine, tmp_path, monkeypatch
):
    """中断只保留已提交批次，续跑沿用两个表的扫描上限。"""
    engine = old_vectors_engine
    args = arguments(tmp_path, batch_size=1)
    original_sleep = backfill.asyncio.sleep

    async def interrupt(delay):
        raise asyncio.CancelledError()

    monkeypatch.setattr(backfill.asyncio, "sleep", interrupt)
    with pytest.raises(asyncio.CancelledError):
        await backfill.run_backfill(engine, engine.url, args)
    state = json.loads(args.checkpoint.read_text(encoding="utf8"))
    assert state["tables"]["thread"]["cursor"] == 1
    assert state["tables"]["booklist"]["cursor"] == 0
    # 扫描期间的新主键不扩大启动上限，在线写入负责其搜索向量。
    async with AsyncSession(engine) as session:
        session.add(
            Thread(id=4, title="新軟體", thread_id=104, channel_id=1, author_id=1)
        )
        session.add(Booklist(id=4, title="新軟體", owner_id=1))
        await session.commit()
    inserted = {
        table: (await snapshot(engine, table))[-1] for table in ("thread", "booklist")
    }
    monkeypatch.setattr(backfill.asyncio, "sleep", original_sleep)
    args.resume = True
    state = await backfill.run_backfill(engine, engine.url, args)
    assert all(
        progress["cursor"] == progress["upper_bound"] == 3
        for progress in state["tables"].values()
    )
    for table in ("thread", "booklist"):
        rows = await snapshot(engine, table)
        assert rows[-1] == inserted[table]
        assert rows[0]["search_vector"] != "'legacy':1"
        assert rows[1]["search_vector"] != "'legacy':1"
        assert rows[2]["search_vector"] is None


@pytest.mark.asyncio
async def test_failed_atomic_save_replays_committed_batch(
    old_vectors_engine, tmp_path, monkeypatch
):
    """数据库提交后文件替换失败，原检查点有效且续跑安全重复处理。"""
    engine = old_vectors_engine
    args = arguments(tmp_path, "thread", 1)
    original_replace = backfill.os.replace
    calls = 0

    def fail_second_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated disk failure")
        original_replace(source, destination)

    monkeypatch.setattr(backfill.os, "replace", fail_second_replace)
    with pytest.raises(OSError):
        await backfill.run_backfill(engine, engine.url, args)
    assert (
        json.loads(args.checkpoint.read_text(encoding="utf8"))["tables"]["thread"][
            "cursor"
        ]
        == 0
    )
    assert (await snapshot(engine, "thread"))[0]["search_vector"] != "'legacy':1"
    assert list(tmp_path.glob(".checkpoint.json.*")) == []
    monkeypatch.setattr(backfill.os, "replace", original_replace)
    args.resume = True
    state = await backfill.run_backfill(engine, engine.url, args)
    assert state["tables"]["thread"]["processed"] == 3
    await assert_vectors_match_sources(engine, "thread")


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["thread", "booklist"])
@pytest.mark.parametrize("field", ["title", "body"])
async def test_concurrent_edit_recomputes_without_stale_vector(
    old_vectors_engine, tmp_path, monkeypatch, table, field
):
    """另一个事务在读取后编辑原文，回填必须重算并保留其业务变更。"""
    engine = old_vectors_engine
    args = arguments(tmp_path, table)
    original_update = SearchVectorBackfillRepository.update_batch
    body_column = "first_message_excerpt" if table == "thread" else "description"
    column = "title" if field == "title" else body_column
    calls = 0

    async def concurrent_update(repository, sources):
        nonlocal calls
        calls += 1
        if calls == 1:
            async with engine.begin() as writer:
                await writer.execute(
                    text(f"UPDATE {table} SET {column} = :value WHERE id = 1"),
                    {"value": "寬頻 記憶體模組"},
                )
        return await original_update(repository, sources)

    monkeypatch.setattr(
        SearchVectorBackfillRepository, "update_batch", concurrent_update
    )
    state = await backfill.run_backfill(engine, engine.url, args)
    assert calls == 2
    assert state["tables"][table]["processed"] == 3
    assert (await snapshot(engine, table))[0][column] == "寬頻 記憶體模組"
    await assert_vectors_match_sources(engine, table)


@pytest.mark.asyncio
async def test_lock_wait_rechecks_source_text(
    old_vectors_engine, tmp_path, monkeypatch
):
    """在更新语句等待行锁期间发生修改，PostgreSQL 仍须重检快照条件。"""
    engine = old_vectors_engine
    original_update = SearchVectorBackfillRepository.update_batch
    calls = 0

    async def locked_update(repository, sources):
        nonlocal calls
        calls += 1
        if calls != 1:
            return await original_update(repository, sources)
        task = None
        try:
            async with engine.begin() as writer:
                await writer.execute(
                    text("UPDATE thread SET title = '新軟體' WHERE id = 1")
                )
                pid = (
                    await repository.connection.execute(text("SELECT pg_backend_pid()"))
                ).scalar_one()
                task = asyncio.create_task(original_update(repository, sources))
                # 等待真实行锁阻塞，随后提交并发编辑使 UPDATE 重检快照。
                for _ in range(100):
                    waiting = (
                        await writer.execute(
                            text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"),
                            {"pid": pid},
                        )
                    ).scalar_one()
                    if waiting:
                        break
                    await asyncio.sleep(0.01)
                assert waiting
            return await task
        finally:
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    monkeypatch.setattr(SearchVectorBackfillRepository, "update_batch", locked_update)
    await backfill.run_backfill(engine, engine.url, arguments(tmp_path, "thread"))
    assert calls == 2
    await assert_vectors_match_sources(engine, "thread")


@pytest.mark.asyncio
async def test_conflict_exhaustion_rolls_back_entire_batch(
    old_vectors_engine, tmp_path, monkeypatch, capsys
):
    """重试三次仍冲突，整批回滚且检查点保持原游标。"""
    engine = old_vectors_engine
    args = arguments(tmp_path, "thread")
    original_update = SearchVectorBackfillRepository.update_batch
    calls = 0

    async def always_conflict(repository, sources):
        nonlocal calls
        calls += 1
        async with engine.begin() as writer:
            await writer.execute(
                text("UPDATE thread SET title = :title WHERE id = 2"),
                {"title": f"寬頻 {calls}"},
            )
        return await original_update(repository, sources)

    monkeypatch.setattr(SearchVectorBackfillRepository, "update_batch", always_conflict)
    with pytest.raises(RuntimeError, match="重试耗尽"):
        await backfill.run_backfill(engine, engine.url, args)
    assert calls == 4
    assert (
        json.loads(args.checkpoint.read_text(encoding="utf8"))["tables"]["thread"][
            "cursor"
        ]
        == 0
    )
    rows = await snapshot(engine, "thread")
    assert rows[0]["search_vector"] == rows[2]["search_vector"] == "'legacy':1"
    assert "失败=1" in capsys.readouterr().out
    monkeypatch.setattr(SearchVectorBackfillRepository, "update_batch", original_update)
    args.resume = True
    await backfill.run_backfill(engine, engine.url, args)
    await assert_vectors_match_sources(engine, "thread")


@pytest.mark.asyncio
async def test_concurrent_deletion_is_counted(
    old_vectors_engine, tmp_path, monkeypatch
):
    """已删除记录无需写回，批次可安全推进并单独统计。"""
    engine = old_vectors_engine
    original_update = SearchVectorBackfillRepository.update_batch

    async def delete_before_update(repository, sources):
        async with engine.begin() as writer:
            await writer.execute(text("DELETE FROM thread WHERE id = 2"))
        return await original_update(repository, sources)

    monkeypatch.setattr(
        SearchVectorBackfillRepository, "update_batch", delete_before_update
    )
    state = await backfill.run_backfill(
        engine, engine.url, arguments(tmp_path, "thread")
    )
    assert state["tables"]["thread"] == {
        "cursor": 3,
        "upper_bound": 3,
        "processed": 2,
        "deleted": 1,
    }
    await assert_vectors_match_sources(engine, "thread")


@pytest.mark.parametrize(
    "field,value",
    [
        ("database", {}),
        ("normalization_version", "old"),
        ("format_version", 0),
        ("tables", {}),
        ("cursor", -1),
        ("upper_bound", -1),
        ("cursor", 4),
        ("processed", True),
    ],
)
def test_resume_rejects_inconsistent_checkpoint(tmp_path, field, value):
    """错误数据库、规则、表选择及游标均不能继续写入。"""
    database = {"host": "localhost", "database": "test", "schema": "test_backfill"}
    state = {
        "format_version": backfill.CHECKPOINT_FORMAT_VERSION,
        "database": database,
        "normalization_version": backfill.SEARCH_NORMALIZATION_VERSION,
        "tables": {
            "thread": {"cursor": 0, "upper_bound": 3, "processed": 0, "deleted": 0}
        },
    }
    invalid = copy.deepcopy(state)
    if field in ("cursor", "upper_bound", "processed"):
        invalid["tables"]["thread"][field] = value
    else:
        invalid[field] = value
    checkpoint = tmp_path / "checkpoint.json"
    backfill.save_checkpoint(checkpoint, invalid)
    with pytest.raises(ValueError):
        backfill.load_checkpoint(checkpoint, database, ("thread",))


@pytest.mark.parametrize(
    "argv",
    [["--batch-size", "0"], ["--sleep", "-1"], ["--sleep", "nan"], ["--sleep", "inf"]],
)
def test_invalid_cli_parameters(argv):
    """拒绝不安全的批次大小和间隔。"""
    with pytest.raises(SystemExit):
        backfill.parse_args(argv)


def test_cli_nonzero_exit_and_missing_url(tmp_path, monkeypatch):
    """缺失数据库配置或冲突失败必须返回非零退出码。"""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    argv = ["--checkpoint", str(tmp_path / "checkpoint.json")]
    assert backfill.main(argv) == 1
    monkeypatch.setattr(
        backfill, "async_main", AsyncMock(side_effect=RuntimeError("并发冲突重试耗尽"))
    )
    assert backfill.main(argv) == 1
