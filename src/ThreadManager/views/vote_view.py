"""标签投票视图：展示标签评分界面并处理投票交互。"""

import logging

import discord

from ThreadManager.views.components.vote_button import TagVoteButton

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

    async def handle_vote(self, button, interaction):
        """历史原生投票消息不再允许修改数据。"""
        await interaction.response.send_message(
            "DC 原生标签为只读，不再支持投票。", ephemeral=True
        )
