import discord
import logging
from shared.safe_defer import safe_defer

from ..thread_manager_service import ThreadManagerService
from .components.vote_button import TagVoteButton

logger = logging.getLogger(__name__)


class TagVoteView(discord.ui.View):
    """标签投票视图"""

    def __init__(
        self,
        thread_id: int,
        thread_name: str,
        tag_map: dict[int, str],
        api_scheduler,
        session_factory,
    ):
        super().__init__(timeout=180)
        self.thread_id = thread_id
        self.thread_name = thread_name
        self.tag_map = tag_map
        self.api_scheduler = api_scheduler
        self.session_factory = session_factory

        # 对标签进行一次性排序，以确保所有地方的顺序一致
        self.sorted_tags = sorted(self.tag_map.items(), key=lambda item: item[1])

        # 创建按钮
        self.create_buttons()

    def create_buttons(self):
        """创建投票按钮并添加到视图中"""
        self.clear_items()

        # 使用排序后的标签列表
        tags = self.sorted_tags

        # 点赞按钮
        for i, (tag_id, tag_name) in enumerate(tags):
            self.add_item(
                TagVoteButton(
                    tag_id,
                    tag_name,
                    vote_value=1,
                    row=i // 5,
                    callback=self.handle_vote,
                )
            )

        # 点踩按钮
        base_row = (len(tags) - 1) // 5 + 1
        for i, (tag_id, tag_name) in enumerate(tags):
            self.add_item(
                TagVoteButton(
                    tag_id,
                    tag_name,
                    vote_value=-1,
                    row=base_row + (i // 5),
                    callback=self.handle_vote,
                )
            )

    async def handle_vote(
        self, button: TagVoteButton, interaction: discord.Interaction
    ):
        """处理按钮点击"""
        await safe_defer(interaction)
        try:
            async with self.session_factory() as session:
                repo = ThreadManagerService(session)
                # 调用repo方法，返回更新后的统计数据
                updated_stats = await repo.record_tag_vote(
                    user_id=interaction.user.id,
                    thread_id=self.thread_id,
                    tag_id=button.tag_id,
                    vote_value=button.vote_value,
                    tag_map=self.tag_map,
                )

            # 投票成功后，使用返回的最新数据更新视图
            await self.update_view(interaction, updated_stats)

        except Exception as e:
            logger.error(f"记录标签投票时出错: {e}")

            error_coro = interaction.followup.send(
                "处理您的评价时发生错误，请稍后再试。", ephemeral=True
            )
            await self.api_scheduler.submit(coro_factory=lambda: error_coro, priority=1)

    async def update_view(self, interaction: discord.Interaction, stats: dict):
        """视图更新入口，接收统计数据作为参数"""
        embed = self.create_embed(stats)
        edit_coro = interaction.edit_original_response(embed=embed, view=self)
        await self.api_scheduler.submit(coro_factory=lambda: edit_coro, priority=1)

    def create_embed(self, stats: dict) -> discord.Embed:
        """
        使用传入的统计数据创建embed
        """
        embed = discord.Embed(
            title=f"帖子 “{self.thread_name}” 的标签评价", color=discord.Color.blue()
        )

        # 使用在初始化时排序好的标签列表
        if not self.sorted_tags:
            embed.description = "该帖子没有应用任何标签。"
            return embed

        for tag_id, tag_name in self.sorted_tags:
            tag_stats = stats.get(tag_name, {})
            up_votes = tag_stats.get("upvotes", 0)
            down_votes = tag_stats.get("downvotes", 0)
            score = tag_stats.get("score", 0)

            embed.add_field(
                name=f"**{tag_name}**",
                value=f"👍 {up_votes} \u2003\u2003 👎 {down_votes} \u2003\u2003 (总分: **{score}**)",
                inline=False,
            )
        return embed
