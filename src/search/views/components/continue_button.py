import discord
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...cog import Search
    from ...dto.search_state import SearchStateDTO


class ContinueButton(discord.ui.Button):
    """用于从超时状态恢复视图的按钮。"""

    def __init__(
        self, cog: "Search", original_interaction: discord.Interaction, state: dict
    ):
        super().__init__(label="🔄 继续搜索", style=discord.ButtonStyle.primary)
        self.cog = cog
        self.original_interaction = original_interaction
        self.state = state

    async def callback(self, interaction: discord.Interaction):
        # 懒加载以避免循环导入
        from ..generic_search_view import GenericSearchView
        from ...dto.search_state import SearchStateDTO

        # 从 state 字典重建 SearchStateDTO
        # 注意：需要确保 on_timeout 保存的状态与 SearchStateDTO 字段兼容
        search_state = SearchStateDTO(**self.state)

        # 创建一个新的 GenericSearchView 实例并传入恢复的状态
        view = GenericSearchView(
            cog=self.cog,
            interaction=self.original_interaction,
            search_state=search_state,
        )

        # 使用恢复的状态更新视图。
        # rerun_search=True 会让视图根据恢复的状态重新执行一次搜索
        await view.update_view(interaction, rerun_search=True)
