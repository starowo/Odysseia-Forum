"""Bot 进程使用的轻量 discord.py 兼容补丁。"""

from __future__ import annotations

import logging
from typing import Any

import discord

logger = logging.getLogger(__name__)

_THREAD_MEMBERS_UPDATE = "THREAD_MEMBERS_UPDATE"
_PATCH_MARKER = "__odysseia_uncached_thread_members_patch__"


def install_uncached_thread_members_patch(bot: Any) -> bool:
    """为 discord.py 本地缓存中不存在的帖子补发成员移除事件。

    discord.py 遇到未知帖子的 ``THREAD_MEMBERS_UPDATE`` 时通常会直接丢弃事件。
    此处只替换这一项解析器，其他情况全部交回原解析器处理。补丁安装采用
    尽力而为策略，确保未来 discord.py 内部接口发生变化时不会阻止 Bot 启动。
    """
    try:
        connection = getattr(bot, "_connection", None)
        parsers = getattr(connection, "parsers", None)
        if parsers is None:
            raise RuntimeError("ConnectionState.parsers 不存在")

        original_parser = parsers.get(_THREAD_MEMBERS_UPDATE)
        if not callable(original_parser):
            raise RuntimeError("THREAD_MEMBERS_UPDATE parser 不存在或不可调用")

        # 避免重复安装补丁，防止热重载或重复初始化时把解析器包多层。
        if getattr(original_parser, _PATCH_MARKER, False):
            return True

        def parse_thread_members_update(data: dict[str, Any]) -> None:
            try:
                # 只有存在移除成员时，才需要为未缓存帖子补发取消关注事件。
                removed_member_ids = data.get("removed_member_ids", [])
                if removed_member_ids:
                    guild = bot.get_guild(int(data["guild_id"]))
                    thread_id = int(data["id"])
                    # 缓存命中的帖子继续交给 discord.py 原实现，避免重复派发。
                    if guild is not None and guild.get_thread(thread_id) is None:
                        # 未缓存帖子时，discord.py 原解析器会直接丢弃这类事件，
                        # 这里补发原始事件，让上层沿用既有的数据库回退逻辑。
                        payload = discord.RawThreadMembersUpdate(data)
                        bot.dispatch("raw_thread_member_remove", payload)
                        return
            except Exception:
                # 遇到无法识别的数据结构或接口变化时，仍交给 discord.py
                # 自带的解析器处理，避免补丁影响原有事件流程。
                logger.exception(
                    "归档帖子成员事件补偿处理失败，已回退 discord.py 原解析器"
                )

            original_parser(data)

        # 标记包装后的解析器，便于后续检测是否已经安装成功。
        setattr(parse_thread_members_update, _PATCH_MARKER, True)
        parsers[_THREAD_MEMBERS_UPDATE] = parse_thread_members_update
        return True
    except Exception as exc:
        logger.error(
            "无法安装归档帖子成员事件兼容补丁；Bot 将继续启动，但未缓存帖子的"
            "移除关注事件可能丢失。discord.py=%s，原因=%s",
            getattr(discord, "__version__", "unknown"),
            exc,
            exc_info=True,
        )
        return False
