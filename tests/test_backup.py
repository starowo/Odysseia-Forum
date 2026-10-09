"""测试数据库定时备份命令。"""

from unittest.mock import MagicMock

import pytest

from backup import cog as backup_cog


def test_create_compressed_backup_uses_zstd_level_6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """数据库快照应使用 custom 格式和 zstd:6 压缩。"""
    run_mock = MagicMock()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://odysseia:secret@postgres:5432/odysseia",
    )
    monkeypatch.setattr(backup_cog.subprocess, "run", run_mock)

    backup = backup_cog.BackupCog.__new__(backup_cog.BackupCog)
    dump_path = backup._create_compressed_backup_sync()

    run_mock.assert_called_once_with(
        [
            "pg_dump",
            "--dbname",
            "postgresql://odysseia:secret@postgres:5432/odysseia",
            "--format",
            "custom",
            "--compress",
            "zstd:6",
            "--file",
            dump_path,
            "--no-owner",
            "--no-acl",
        ],
        check=True,
        capture_output=True,
    )
    assert dump_path.startswith("data/backup_temp_")
    assert dump_path.endswith(".dump")
