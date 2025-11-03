import discord
from typing import TYPE_CHECKING, List

from .base_management_view import BaseManagementView
from .thread_select import ThreadSelect
from shared.enum.collection_type import CollectionType

if TYPE_CHECKING:
    pass


class BatchCollectView(BaseManagementView):
    """批量收藏视图"""

    def create_components(self) -> List[discord.ui.Item]:
        """创建此视图特有的组件，即帖子选择菜单"""
        return [
            ThreadSelect(
                threads=self.threads,
                selected_threads=self.selected_threads,
                on_change_callback=self.on_selected_threads_change,
            )
        ]

    def get_action_buttons(self) -> List[discord.ui.Item]:
        """获取操作按钮"""
        return [self.collect_all_button, self.collect_selected_button]

    @discord.ui.button(
        label="收藏全部帖子",
        row=1,
        style=discord.ButtonStyle.success,
        custom_id="collect_all",
    )
    async def collect_all_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Re-fetch all thread IDs without pagination
        all_threads, _ = await self.fetch_data_func(1, 9999)
        thread_ids = [t.thread_id for t in all_threads]

        if not thread_ids:
            await interaction.response.send_message(
                "没有帖子可以收藏。", ephemeral=True, delete_after=10
            )
            return

        async with self.cog.get_collection_service() as service:
            result = await service.add_collections(
                interaction.user.id, CollectionType.THREAD, thread_ids
            )
            await interaction.response.send_message(
                f"操作完成！成功收藏 {result['added']} 个帖子，{result['duplicates']} 个已存在。",
                ephemeral=True,
                delete_after=10,
            )

        # Refresh the view
        await self.update_data()
        await self.update_view(interaction)
        # 刷新主搜索视图
        if self.refresh_callback:
            await self.refresh_callback()

    @discord.ui.button(
        label="收藏选中帖子",
        row=1,
        style=discord.ButtonStyle.primary,
        custom_id="collect_selected",
    )
    async def collect_selected_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not self.selected_threads:
            await interaction.response.send_message(
                "请先选择帖子。", ephemeral=True, delete_after=10
            )
            return

        thread_ids = [int(tid) for tid in self.selected_threads]
        async with self.cog.get_collection_service() as service:
            result = await service.add_collections(
                interaction.user.id, CollectionType.THREAD, thread_ids
            )
            await interaction.response.send_message(
                f"操作完成！成功收藏 {result['added']} 个帖子，{result['duplicates']} 个已存在。",
                ephemeral=True,
                delete_after=10,
            )

        # Clear selection and refresh
        self.selected_threads.clear()
        await self.update_data()
        await self.update_view(interaction)
        # 刷新主搜索视图
        if self.refresh_callback:
            await self.refresh_callback()
