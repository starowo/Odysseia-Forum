from datetime import datetime

import discord

from banner.dto.banner_scope_status import BannerScopeStatus
from shared.enum import TargetType


class BannerStatusView:
    """构建并拆分仅执行者可见的 Banner 状态消息。"""

    @staticmethod
    def build_messages(
        scopes: list[BannerScopeStatus], channel_names: dict[int, str], now: datetime
    ) -> list[str]:
        """按范围展示详情，续条重复范围标题且不超过消息长度限制。"""
        # 清理名称中的换行和 Markdown，保持每条详情的行结构。
        messages: list[str] = []
        current = "📊 Banner系统状态"
        for scope in scopes:
            name = (
                "全频道"
                if scope.channel_id is None
                else channel_names.get(scope.channel_id, str(scope.channel_id))
            )
            name = discord.utils.escape_markdown(" ".join(name.split())[:100])
            header = (
                f"{name}：轮播 {len(scope.items)}/{scope.capacity}"
                f"｜已审核待展示 {scope.waiting_count}"
            )
            if len(current) + len(header) + 2 > 1900:
                messages.append(current)
                current = "📊 Banner系统状态（续）"
            current += f"\n\n{header}"
            lines = []
            for item in scope.items:
                title = " ".join(item.title.split())
                title = title[:30] + "..." if len(title) > 30 else title
                title = discord.utils.escape_markdown(title)
                label = (
                    "频道" if item.target_type == TargetType.CHANNEL.value else "帖子"
                )
                seconds = (item.end_time - now).total_seconds()
                if seconds >= 86400:
                    remaining = f"剩余 {int(seconds // 86400)} 天"
                elif seconds >= 3600:
                    remaining = f"剩余 {int(seconds // 3600)} 小时"
                else:
                    remaining = "剩余不足1小时"
                lines.extend(
                    [
                        f"  • [{label}] {title}",
                        f"    ID：{item.target_id}｜{remaining}",
                    ]
                )
            for line in lines or ["  暂无轮播"]:
                if len(current) + len(line) + 1 > 1900:
                    messages.append(current)
                    current = f"📊 Banner系统状态（续）\n\n{header}"
                current += f"\n{line}"
        messages.append(current)
        return messages
