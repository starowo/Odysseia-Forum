"""更新检测统计查询脚本测试。"""

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "show_update_detector_stats.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "show_update_detector_stats",
    SCRIPT_PATH,
)
assert SCRIPT_SPEC and SCRIPT_SPEC.loader
stats_script = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(stats_script)

ACTUAL_FIELDS = stats_script.ACTUAL_FIELDS
ESTIMATE_FIELDS = stats_script.ESTIMATE_FIELDS
_render_table = stats_script._render_table
_sum_rows = stats_script._sum_rows


def test_estimate_stats_table_contains_daily_and_total_rows():
    """估算表格展示单日数据并生成多日合计。"""
    rows = [
        {
            "date": "20260818",
            "eligible_request_count": 2,
            "estimated_prompt_tokens": 100,
            "estimated_completion_tokens_upper_bound": 4096,
            "estimated_total_tokens_upper_bound": 4196,
        },
        {
            "date": "20260819",
            "eligible_request_count": 3,
            "estimated_prompt_tokens": 150,
            "estimated_completion_tokens_upper_bound": 6144,
            "estimated_total_tokens_upper_bound": 6294,
        },
    ]

    total = _sum_rows(rows, ESTIMATE_FIELDS)
    table = _render_table("estimate", rows, total)

    assert total["eligible_request_count"] == 5
    assert total["estimated_prompt_tokens"] == 250
    assert "20260818" in table
    assert "20260819" in table
    assert "TOTAL" in table


def test_actual_stats_total_sums_token_usage():
    """正式统计合计真实请求次数和 Token usage。"""
    rows = [
        {
            "request_attempt_count": 2,
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
        },
        {
            "request_attempt_count": 1,
            "prompt_tokens": 50,
            "completion_tokens": 10,
            "total_tokens": 60,
        },
    ]

    total = _sum_rows(rows, ACTUAL_FIELDS)

    assert total["request_attempt_count"] == 3
    assert total["prompt_tokens"] == 150
    assert total["completion_tokens"] == 30
    assert total["total_tokens"] == 180
