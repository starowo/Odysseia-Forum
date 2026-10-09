"""测试 healthcheck.py 中的 Docker 健康检查逻辑。

覆盖 8 个场景，确保各种 Bot 状态下返回正确的退出码。"""

import json
import time
from pathlib import Path

import pytest

# 导入健康检查脚本（与 bot_main.py 不在同一模块树中）
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from healthcheck import main, MAX_HEARTBEAT_AGE, MAX_DISCONNECT_TIME


def _write_heartbeat(path: Path, data: dict) -> None:
    """将心跳状态写入临时文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class TestHealthcheck:
    """健康检查主逻辑测试。"""

    # ── 场景 1：心跳文件不存在 ──────────────────────────────────
    def test_file_not_found(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent.json"
        result = main(str(nonexistent))
        assert result == 1

    # ── 场景 2：正常已连接 ─────────────────────────────────────
    def test_connected(self, tmp_path: Path):
        hb_file = tmp_path / "healthy.json"
        _write_heartbeat(
            hb_file,
            {
                "timestamp": time.time(),
                "connected": True,
                "disconnected_since": 0,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 0

    # ── 场景 3：未连接但 disconnected_since=0（启动中） ─────────
    def test_starting_up_disconnected_since_zero(self, tmp_path: Path):
        hb_file = tmp_path / "starting.json"
        _write_heartbeat(
            hb_file,
            {
                "timestamp": time.time(),
                "connected": False,
                "disconnected_since": 0,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 0

    # ── 场景 4：心跳时间戳过期（事件循环阻塞） ──────────────────
    def test_heartbeat_expired(self, tmp_path: Path):
        hb_file = tmp_path / "expired.json"
        _write_heartbeat(
            hb_file,
            {
                "timestamp": time.time() - MAX_HEARTBEAT_AGE - 10,
                "connected": True,
                "disconnected_since": 0,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 1

    # ── 场景 5：Bot 已关闭 ─────────────────────────────────────
    def test_bot_closed(self, tmp_path: Path):
        hb_file = tmp_path / "closed.json"
        _write_heartbeat(
            hb_file,
            {
                "timestamp": time.time(),
                "connected": False,
                "disconnected_since": 0,
                "is_closed": True,
            },
        )
        result = main(str(hb_file))
        assert result == 1

    # ── 场景 6：断连时长超过阈值 ────────────────────────────────
    def test_disconnect_too_long(self, tmp_path: Path):
        hb_file = tmp_path / "long_disconnect.json"
        now = time.time()
        _write_heartbeat(
            hb_file,
            {
                "timestamp": now,
                "connected": False,
                # disconnected_since 必须用 wall-clock 时间戳（与 P0 修复一致）
                "disconnected_since": now - MAX_DISCONNECT_TIME - 10,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 1

    # ── 场景 7：短暂断连，仍在重连中 ────────────────────────────
    def test_brief_disconnect_still_reconnecting(self, tmp_path: Path):
        hb_file = tmp_path / "brief_disconnect.json"
        now = time.time()
        _write_heartbeat(
            hb_file,
            {
                "timestamp": now,
                "connected": False,
                "disconnected_since": now - 30,  # 仅断连 30 秒
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 0

    # ── 场景 8：JSON 文件损坏 ──────────────────────────────────
    def test_corrupt_json(self, tmp_path: Path):
        hb_file = tmp_path / "corrupt.json"
        hb_file.parent.mkdir(parents=True, exist_ok=True)
        hb_file.write_text("this is not valid json {{{")
        result = main(str(hb_file))
        assert result == 1

    # ── 场景 9（边界）：断连刚好在阈值边界 ─────────────────────
    def test_disconnect_at_threshold(self, tmp_path: Path):
        """断连刚好 300 秒时视为「未超过阈值」，仍返回健康。"""
        hb_file = tmp_path / "at_threshold.json"
        now = time.time()
        _write_heartbeat(
            hb_file,
            {
                "timestamp": now,
                "connected": False,
                # 留 1 秒缓冲，避免写入到读取间的毫秒级延迟导致边界误判
                "disconnected_since": now - MAX_DISCONNECT_TIME + 1,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 0


class TestHealthcheckEdgeCases:
    """额外的边界场景。"""

    def test_missing_timestamp_field(self, tmp_path: Path):
        """timestamp 缺失 → age 以大值计算 → 触发心跳过期。"""
        hb_file = tmp_path / "missing_ts.json"
        _write_heartbeat(
            hb_file,
            {
                "connected": True,
                "disconnected_since": 0,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 1  # age = now - 0 ≈ 17.5 亿秒 > 90s

    def test_missing_connected_field(self, tmp_path: Path):
        """connected 缺失 → 视为 False → 走断连检查路径。"""
        hb_file = tmp_path / "missing_conn.json"
        now = time.time()
        _write_heartbeat(
            hb_file,
            {
                "timestamp": now,
                "disconnected_since": 0,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 0  # disconnected_since=0 → "启动中"

    def test_disconnected_since_is_none(self, tmp_path: Path):
        """disconnected_since 为 null/None → 视为启动中。"""
        hb_file = tmp_path / "null_ds.json"
        _write_heartbeat(
            hb_file,
            {
                "timestamp": time.time(),
                "connected": False,
                "disconnected_since": None,
                "is_closed": False,
            },
        )
        result = main(str(hb_file))
        assert result == 0

    def test_junk_permissions_error(self, tmp_path: Path):
        """测试无法读取的文件（无权限）时返回不健康。"""
        # 跳过 Windows：权限模型不同
        if os.name == "nt":
            pytest.skip("Windows 不支持 Unix 权限模型")

        hb_file = tmp_path / "no_perms.json"
        _write_heartbeat(
            hb_file,
            {
                "timestamp": time.time(),
                "connected": True,
                "disconnected_since": 0,
                "is_closed": False,
            },
        )
        hb_file.chmod(0o000)
        try:
            result = main(str(hb_file))
            assert result == 1
        finally:
            hb_file.chmod(0o644)
