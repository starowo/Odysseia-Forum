from typing import Awaitable, Callable, List, Set

import discord

from models import Thread


class ThreadSelect(discord.ui.Select):
    """帖子多选菜单，支持跨页保持选中状态"""

    def __init__(
        self,
        threads: List[Thread],
        selected_threads: Set[str],
        on_change_callback: Callable[[discord.Interaction, Set[str]], Awaitable[None]],
        **kwargs,
    ):
        self.threads = threads
        self.selected_threads = selected_threads
        self.on_change_callback = on_change_callback

        # 构建选项
        options = [
            discord.SelectOption(
                label=thread.title[:100],
                value=str(thread.thread_id),
            )
            for thread in threads
        ]

        # 设置 placeholder
        if self.selected_threads:
            placeholder_text = f"已选中 {len(self.selected_threads)} 个帖子"
        else:
            placeholder_text = "选择要操作的帖子..."

        super().__init__(
            placeholder=placeholder_text,
            options=options
            if options
            else [discord.SelectOption(label="无可用帖子", value="no_threads")],
            min_values=0,
            max_values=len(options) if options else 1,
            custom_id="thread_select",
            disabled=not options,
            **kwargs,
        )

        # 选项的默认状态由父视图根据 self.selected_threads 在每次更新时设置
        for option in self.options:
            if option.value in self.selected_threads:
                option.default = True

    async def callback(self, interaction: discord.Interaction):
        """当用户在下拉菜单中做出选择时调用"""

        # 用户在当前页的新选择（排除占位符）
        current_page_selection = {v for v in self.values if v != "no_threads"}

        # 直接使用当前页的选择覆盖旧的选择
        # 因为我们现在只关心本页的选项
        await self.on_change_callback(interaction, current_page_selection)
