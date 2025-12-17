import re
from datetime import timezone

import discord

from models import Thread as ThreadModel


class ThreadEmbedBuilder:
    """负责构建帖子搜索结果的 Embed"""

    @staticmethod
    def _highlight_keywords(text: str, highlight_pattern: re.Pattern | None) -> str:
        """辅助函数，使用预编译的 pattern 在文本中高亮关键词"""
        if not highlight_pattern or not text:
            return text

        # 直接使用传入的 pattern 对象进行替换
        return highlight_pattern.sub(r" **\1** ", text)

    @staticmethod
    async def build(
        thread: "ThreadModel",
        guild: discord.Guild,
        preview_mode: str = "thumbnail",
        keywords_str: str = "",
        highlight_pattern: re.Pattern | None = None,  # 接收 pattern 对象
    ) -> discord.Embed:
        """根据Thread ORM对象构建嵌入消息"""

        author_display = f"作者 <@{thread.author_id}>"

        embed = discord.Embed(
            title=thread.title,
            description=author_display,
            url=f"https://discord.com/channels/{guild.id}/{thread.thread_id}",
        )

        # 标签信息通过 relationship 加载
        tag_names = [tag.name for tag in thread.tags]

        # 将 datetime 对象转换为 Unix 时间戳
        created_at_ts = int(thread.created_at.replace(tzinfo=timezone.utc).timestamp())

        # 使用 Discord 动态时间戳格式
        if thread.last_active_at:
            last_active_ts = int(
                thread.last_active_at.replace(tzinfo=timezone.utc).timestamp()
            )
            last_active_str = f"<t:{last_active_ts}:F>"
        else:
            last_active_str = "无"

        basic_stats = (
            f"发帖日期: <t:{created_at_ts}:D> | "
            f"最近活跃: {last_active_str}\n"
            f"最高反应数: **{thread.reaction_count}** | 总回复数: **{thread.reply_count}**\n"
            f"标签: **{', '.join(tag_names) if tag_names else '无'}**"
        )

        embed.add_field(
            name="统计",
            value=basic_stats,
            inline=False,
        )

        # 首楼摘要
        excerpt = thread.first_message_excerpt or ""
        excerpt_display = (
            excerpt[:200] + "..." if len(excerpt) > 200 else (excerpt or "无内容")
        )

        # 高亮摘要
        highlighted_excerpt = ThreadEmbedBuilder._highlight_keywords(
            excerpt_display, highlight_pattern
        )

        embed.add_field(name="首楼摘要", value=highlighted_excerpt, inline=False)

        # 根据用户偏好设置预览图显示方式（使用首张图片）
        preview_url = thread.thumbnail_urls[0] if thread.thumbnail_urls else None
        if preview_url:
            if preview_mode == "image":
                embed.set_image(url=preview_url)
            else:  # thumbnail
                embed.set_thumbnail(url=preview_url)

        return embed
