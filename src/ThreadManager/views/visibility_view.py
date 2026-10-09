"""帖子可见性切换视图：首楼被删除后允许贴主恢复或隐藏帖子。"""

import discord
import logging
from typing import TYPE_CHECKING
from core.thread_repository import ThreadRepository
from shared.redis_client import RedisManager
from shared.safe_defer import safe_defer
from shared.similar_threads_cache import invalidate_similar_candidate_pools

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class ThreadVisibilityView(discord.ui.View):
    """
    帖子可见性切换持久化视图。
    当首楼被删除时，弹出此视图允许贴主恢复或再次隐藏帖子。
    """

    def __init__(self, bot: "MyBot", session_factory):
        super().__init__(timeout=None)
        self.bot = bot
        self.session_factory = session_factory

    @discord.ui.button(
        label="切换帖子搜索可见性",
        style=discord.ButtonStyle.primary,
        custom_id="persistent:toggle_thread_visibility",
        emoji="👁️",
    )
    async def toggle_visibility(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ 此命令只能在帖子中使用。", ephemeral=True
            )
            return

        thread = interaction.channel

        # 权限校验：仅贴主或管理员可操作
        is_admin = interaction.user.id in self.bot.config.get("bot_admin_user_ids", [])
        if thread.owner_id is None or (
            interaction.user.id != thread.owner_id and not is_admin
        ):
            await interaction.response.send_message(
                "❌ 只有帖子作者可以修改帖子可见性。", ephemeral=True
            )
            return

        await safe_defer(interaction)

        try:
            async with self.session_factory() as session:
                repo = ThreadRepository(session)
                current_status = await repo.get_thread_visibility(thread.id)

                if current_status is None:
                    await interaction.followup.send(
                        "❌ 在数据库中未找到此帖子记录", ephemeral=True
                    )
                    return

                new_status = not current_status
                await repo.update_thread_visibility(thread.id, new_status)

            # 可见性变化会改变推荐资格，立即清除源帖的两类候选池。
            try:
                await invalidate_similar_candidate_pools(
                    RedisManager.get_client(), thread.id
                )
            except Exception:
                logger.warning(
                    "失效相似帖子候选池失败: thread_id=%s",
                    thread.id,
                    exc_info=True,
                )

            status_text = "可见" if new_status else "隐藏"
            await interaction.followup.send(
                f"✅ 帖子的搜索可见性已成功切换。\n当前状态：**{status_text}**",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"切换帖子 {thread.id} 可见性时发生错误: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ 切换失败，发生内部错误。", ephemeral=True
            )
