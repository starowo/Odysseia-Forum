"""从数据库原文独立回填帖子和书单搜索向量，不调用 Discord。"""

import argparse
import asyncio
import copy
import json
import math
import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# 支持直接执行脚本以及镜像中已有的 PYTHONPATH。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.search_vector_backfill_repository import SearchVectorBackfillRepository  # noqa: E402
from dto.search.search_vector_source_dto import SearchVectorSourceDTO  # noqa: E402
from shared.search_normalization import SEARCH_NORMALIZATION_VERSION  # noqa: E402
from shared.text_utils import build_search_vector_text  # noqa: E402

CHECKPOINT_FORMAT_VERSION = 1
MAX_CONFLICT_RETRIES = 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析并校验手动回填参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", choices=("all", "thread", "booklist"), default="all")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument(
        "--checkpoint", type=Path, default=Path("data/search-vector-backfill.json")
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.batch_size <= 0:
        parser.error("--batch-size 必须大于 0")
    if not math.isfinite(args.sleep) or args.sleep < 0:
        parser.error("--sleep 必须为有限的非负秒数")
    return args


def save_checkpoint(path: Path, state: dict) -> None:
    """在同目录写入并同步临时文件，再原子替换检查点。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        # 文件落盘后才替换；失败时原检查点仍可续跑已提交批次。
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as checkpoint_file:
            temporary_path = Path(checkpoint_file.name)
            json.dump(state, checkpoint_file, ensure_ascii=False, indent=2)
            checkpoint_file.write("\n")
            checkpoint_file.flush()
            os.fsync(checkpoint_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_checkpoint(path: Path, database: dict, tables: tuple[str, ...]) -> dict:
    """续跑时验证数据库、规则版本、所选表及主键范围一致。"""
    with path.open(encoding="utf-8") as checkpoint_file:
        state = json.load(checkpoint_file)
    if not isinstance(state, dict):
        raise ValueError("检查点格式无效")
    if state.get("format_version") != CHECKPOINT_FORMAT_VERSION:
        raise ValueError("检查点格式版本不一致")
    if state.get("database") != database:
        raise ValueError("检查点数据库标识不一致")
    if state.get("normalization_version") != SEARCH_NORMALIZATION_VERSION:
        raise ValueError("检查点规范化规则版本不一致")
    if not isinstance(state.get("tables"), dict) or set(state["tables"]) != set(tables):
        raise ValueError("检查点表范围与 --table 不一致")
    for table_state in state["tables"].values():
        if not isinstance(table_state, dict):
            raise ValueError("检查点表状态无效")
        for field in ("cursor", "upper_bound", "processed", "deleted"):
            if type(table_state.get(field)) is not int or table_state[field] < 0:
                raise ValueError(f"检查点 {field} 无效")
        if table_state["cursor"] > table_state["upper_bound"]:
            raise ValueError("检查点游标超过扫描上限")
    return state


async def get_database_identity(engine: AsyncEngine, url: URL) -> dict:
    """读取不含密码或连接查询参数的数据库和 schema 标识。"""
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT current_database(), current_schema()")
        )
        database, schema = result.one()
    # 使用实际连接目标，避免不同 schema 的检查点互用。
    return {
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "database": database,
        "username": url.username,
        "schema": schema,
    }


def prepare_sources(
    sources: list[SearchVectorSourceDTO],
) -> list[SearchVectorSourceDTO]:
    """使用与在线写入相同的函数批量计算搜索分词。"""
    # CPU 工作在调用端线程池执行，不阻塞异步数据库操作。
    return [
        source.model_copy(
            update={"tokens": build_search_vector_text(source.title, source.body)}
        )
        for source in sources
    ]


async def process_batch(
    repository: SearchVectorBackfillRepository, sources: list[SearchVectorSourceDTO]
) -> tuple[int, int]:
    """写入一批向量，并对冲突记录重新读取重算至多三次。"""
    pending = sources
    updated_count = 0
    deleted_count = 0
    for attempt in range(MAX_CONFLICT_RETRIES + 1):
        prepared = await asyncio.to_thread(prepare_sources, pending)
        updated = await repository.update_batch(prepared)
        updated_count += len(updated)
        pending_ids = [source.id for source in pending if source.id not in updated]
        if not pending_ids:
            return updated_count, deleted_count
        fresh = await repository.read_sources(pending_ids)
        deleted_count += len(pending_ids) - len(fresh)
        if not fresh:
            return updated_count, deleted_count
        if attempt == MAX_CONFLICT_RETRIES:
            print(
                f"{repository.table}: 失败={len(fresh)}，并发冲突重试耗尽，"
                f"主键={[source.id for source in fresh]}，回滚整批",
                flush=True,
            )
            raise RuntimeError("并发冲突重试耗尽，当前批次检查点未推进")
        print(
            f"{repository.table}: 重算并发修改={len(fresh)}，重试={attempt + 1}",
            flush=True,
        )
        pending = fresh
    raise AssertionError("不可达的回填状态")


async def run_backfill(engine: AsyncEngine, url: URL, args: argparse.Namespace) -> dict:
    """逐表逐批提交回填，并在成功提交后保存游标。"""
    tables = ("thread", "booklist") if args.table == "all" else (args.table,)
    database = await get_database_identity(engine, url)
    if args.resume:
        state = load_checkpoint(args.checkpoint, database, tables)
    else:
        if args.checkpoint.exists():
            raise ValueError(
                "检查点已存在；续跑请用 --resume，重新扫描请指定新的检查点路径"
            )
        state = {
            "format_version": CHECKPOINT_FORMAT_VERSION,
            "database": database,
            "normalization_version": SEARCH_NORMALIZATION_VERSION,
            "tables": {},
        }
        # 启动时记录所有表上限，新插入的更高主键留给在线索引规则处理。
        async with engine.begin() as connection:
            for table in tables:
                upper_bound = await SearchVectorBackfillRepository(
                    connection, table
                ).get_scan_limit()
                state["tables"][table] = {
                    "cursor": 0,
                    "upper_bound": upper_bound,
                    "processed": 0,
                    "deleted": 0,
                }
        save_checkpoint(args.checkpoint, state)

    print(
        f"规范化规则={SEARCH_NORMALIZATION_VERSION}，检查点={args.checkpoint}",
        flush=True,
    )
    for table in tables:
        progress = state["tables"][table]
        print(
            f"{table}: 游标={progress['cursor']}，扫描上限={progress['upper_bound']}",
            flush=True,
        )
        while progress["cursor"] < progress["upper_bound"]:
            # 每批独立事务，任何错误或中断都回滚未提交的整批。
            async with engine.begin() as connection:
                repository = SearchVectorBackfillRepository(connection, table)
                sources = await repository.get_batch(
                    progress["cursor"], progress["upper_bound"], args.batch_size
                )
                updated, deleted = (
                    await process_batch(repository, sources) if sources else (0, 0)
                )
            next_state = copy.deepcopy(state)
            next_progress = next_state["tables"][table]
            next_progress["cursor"] = (
                sources[-1].id if sources else progress["upper_bound"]
            )
            next_progress["processed"] += updated
            next_progress["deleted"] += deleted
            # 提交后保存失败也不跳过记录，续跑会安全重复已提交的批次。
            save_checkpoint(args.checkpoint, next_state)
            state = next_state
            progress = next_progress
            print(
                f"{table}: 游标={progress['cursor']}/{progress['upper_bound']}，"
                f"已更新={progress['processed']}，已删除={progress['deleted']}，失败=0",
                flush=True,
            )
            if progress["cursor"] < progress["upper_bound"]:
                await asyncio.sleep(args.sleep)
    print("回填完成，失败=0", flush=True)
    return state


async def async_main(args: argparse.Namespace) -> None:
    """使用显式 DATABASE_URL 建立独立连接池，退出时关闭。"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("请设置 DATABASE_URL；脚本不自动选择数据库")
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL 必须指向 PostgreSQL")
    engine = create_async_engine(
        url.set(drivername="postgresql+asyncpg"), pool_size=1, max_overflow=0
    )
    try:
        await run_backfill(engine, url, args)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    """返回明确退出码，不输出可能含密码的数据库异常详情。"""
    args = parse_args(argv)
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("回填已中断；追加 --resume 续跑最后已保存的检查点", file=sys.stderr)
        return 130
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        print(f"回填停止：{error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(
            f"回填停止：{type(error).__name__}，失败=1；当前批次检查点未推进",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
