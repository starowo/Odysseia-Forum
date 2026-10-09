#!/usr/bin/env python3
"""Docker 健康检查脚本 —— 读取 bot 写入的心跳文件判断容器是否健康。

退出码:
  0 = 健康（已连接或短暂断连）
  1 = 不健康（心跳过期 / 长期断连 / 文件不可读 / bot 已关闭）
"""

import json
import sys
import time

HEARTBEAT_FILE = "/app/data/bot_heartbeat.json"  # 与 bot_main.py 同步
MAX_HEARTBEAT_AGE = 90  # 心跳文件最大允许年龄（秒）
MAX_DISCONNECT_TIME = 300  # 最大允许持续断连时长（秒）


def main(heartbeat_file: str | None = None) -> int:
    # 读取心跳文件
    path = heartbeat_file or HEARTBEAT_FILE
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("HEALTHCHECK: 心跳文件未找到（可能正在启动）")
        return 1
    except (json.JSONDecodeError, OSError):
        print("HEALTHCHECK: 心跳文件损坏或不可读")
        return 1

    now = time.time()
    age = now - data.get("timestamp", 0)

    # 检查心跳新鲜度（事件循环阻塞会导致文件过期）
    if age > MAX_HEARTBEAT_AGE:
        print(f"HEALTHCHECK: 心跳过期 ({age:.0f}s > {MAX_HEARTBEAT_AGE}s)")
        return 1

    # 检查 bot 是否已关闭
    if data.get("is_closed", True):
        print("HEALTHCHECK: bot 已关闭")
        return 1

    # 已连接 → 健康
    if data.get("connected", False):
        print("HEALTHCHECK: 已连接到 Discord")
        return 0

    # 未连接 → 检查断连时长
    disconnected_since = data.get("disconnected_since", 0)
    if isinstance(disconnected_since, (int, float)) and disconnected_since > 0:
        duration = now - disconnected_since
        if duration > MAX_DISCONNECT_TIME:
            print(f"HEALTHCHECK: 断连 {duration:.0f}s (>{MAX_DISCONNECT_TIME}s)")
            return 1
        print(f"HEALTHCHECK: 短暂断连 ({duration:.0f}s)，仍在重连中")
        return 0

    # disconnected_since 为 0 或缺失：尚未完成首次连接
    print("HEALTHCHECK: 尚未完成首次连接（启动中）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
