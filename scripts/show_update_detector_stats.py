"""读取并汇总 Redis 中的更新检测 Token 统计。"""

import argparse
import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from redis.asyncio import from_url

ESTIMATE_FIELDS = (
    "eligible_request_count",
    "ascii_character_count",
    "non_ascii_character_count",
    "estimated_content_tokens",
    "chat_overhead_tokens",
    "estimated_prompt_tokens",
    "estimated_completion_tokens_upper_bound",
    "estimated_total_tokens_upper_bound",
)
ACTUAL_FIELDS = (
    "request_attempt_count",
    "api_success_count",
    "api_error_count",
    "decision_yes_count",
    "decision_no_count",
    "invalid_decision_count",
    "truncated_count",
    "usage_missing_count",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
)


def _load_runtime_config() -> dict[str, Any]:
    """读取当前目录下的运行配置。"""
    config_path = Path("config.json")
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def _parse_date(value: str) -> date:
    """解析命令行中的 ISO 日期。"""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"非法日期: {value}") from error


def _build_date_range(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> list[date]:
    """根据 days 或 from/to 构造包含首尾的日期范围。"""
    if bool(args.date_from) != bool(args.date_to):
        parser.error("--from 和 --to 必须同时提供")
    if args.days is not None and args.date_from:
        parser.error("--days 不能与 --from/--to 同时使用")

    if args.date_from and args.date_to:
        start_date = args.date_from
        end_date = args.date_to
        if start_date > end_date:
            parser.error("--from 不能晚于 --to")
    else:
        days = args.days if args.days is not None else 7
        if days <= 0:
            parser.error("--days 必须大于 0")
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)

    return [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    ]


def _normalize_row(raw: dict[str, str], fields: tuple[str, ...]) -> dict[str, Any]:
    """将 Redis Hash 的计数字段转换为整数。"""
    row: dict[str, Any] = dict(raw)
    for field in fields:
        row[field] = int(raw.get(field, 0))
    for field in (
        "thinking_enabled",
        "max_output_tokens",
        "first_recorded_at",
        "last_recorded_at",
    ):
        if field in raw:
            row[field] = int(raw[field])
    return row


async def _read_rows(
    redis_url: str,
    kind: str,
    model: str,
    dates: list[date],
) -> list[dict[str, Any]]:
    """批量读取日期范围内存在的统计 Hash。"""
    redis = from_url(redis_url, decode_responses=True)
    keys = [
        f"update_detector:token_stats:{kind}:{model}:{day.strftime('%Y%m%d')}"
        for day in dates
    ]
    try:
        async with redis.pipeline(transaction=False) as pipeline:
            for key in keys:
                pipeline.hgetall(key)
            results = await pipeline.execute()
    finally:
        await redis.aclose()

    fields = ESTIMATE_FIELDS if kind == "estimate" else ACTUAL_FIELDS
    return [_normalize_row(raw, fields) for raw in results if raw]


def _sum_rows(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, int]:
    """汇总所有日期行的计数字段。"""
    return {field: sum(int(row.get(field, 0)) for row in rows) for field in fields}


def _render_table(kind: str, rows: list[dict[str, Any]], total: dict[str, int]) -> str:
    """将每日统计及合计渲染为等宽文本表格。"""
    if kind == "estimate":
        columns = (
            ("DATE", "date"),
            ("REQUESTS", "eligible_request_count"),
            ("PROMPT_EST", "estimated_prompt_tokens"),
            ("OUTPUT_MAX", "estimated_completion_tokens_upper_bound"),
            ("TOTAL_MAX", "estimated_total_tokens_upper_bound"),
        )
    else:
        columns = (
            ("DATE", "date"),
            ("REQUESTS", "request_attempt_count"),
            ("PROMPT", "prompt_tokens"),
            ("COMPLETION", "completion_tokens"),
            ("TOTAL", "total_tokens"),
        )

    display_rows = [[str(row.get(field, 0)) for _, field in columns] for row in rows]
    total_row = ["TOTAL"] + [str(total.get(field, 0)) for _, field in columns[1:]]
    widths = [
        max(
            len(header),
            *(len(row[index]) for row in display_rows),
            len(total_row[index]),
        )
        for index, (header, _) in enumerate(columns)
    ]
    header_line = "  ".join(
        header.rjust(widths[index]) for index, (header, _) in enumerate(columns)
    )
    body_lines = [
        "  ".join(value.rjust(widths[index]) for index, value in enumerate(row))
        for row in display_rows
    ]
    total_line = "  ".join(
        value.rjust(widths[index]) for index, value in enumerate(total_row)
    )
    return "\n".join([header_line, *body_lines, total_line])


async def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """读取配置、查询 Redis 并输出所需格式。"""
    config = _load_runtime_config()
    detector_config = config.get("update_detector", {})
    model = detector_config.get("deepseek_model", "deepseek-v4-flash")
    redis_url = os.environ.get("REDIS_URL") or config.get(
        "redis_url", "redis://localhost:6379/0"
    )
    dates = _build_date_range(args, parser)
    rows = await _read_rows(redis_url, args.kind, model, dates)
    fields = ESTIMATE_FIELDS if args.kind == "estimate" else ACTUAL_FIELDS
    total = _sum_rows(rows, fields)

    if args.output_format == "json":
        print(
            json.dumps(
                {
                    "kind": args.kind,
                    "model": model,
                    "from": dates[0].isoformat(),
                    "to": dates[-1].isoformat(),
                    "daily": rows,
                    "total": total,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    print(_render_table(args.kind, rows, total))


def main() -> None:
    """解析命令行参数并运行统计查询。"""
    parser = argparse.ArgumentParser(description="查看更新检测 Token 统计")
    parser.add_argument("--kind", choices=("estimate", "actual"), required=True)
    parser.add_argument("--days", type=int)
    parser.add_argument("--from", dest="date_from", type=_parse_date)
    parser.add_argument("--to", dest="date_to", type=_parse_date)
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("table", "json"),
        default="table",
    )
    args = parser.parse_args()
    asyncio.run(_run(args, parser))


if __name__ == "__main__":
    main()
