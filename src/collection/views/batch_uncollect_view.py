from typing import TYPE_CHECKING, List

import discord

from collection.views.base_management_view import BaseManagementView
from collection.views.confirmation_view import ConfirmationView
from collection.views.thread_select import ThreadSelect
from core.collection_service import CollectionService
from core.thread_service import ThreadService
from shared.enum.collection_type import CollectionType

if TYPE_CHECKING:
    pass


class BatchUncollectView(BaseManagementView):
    """批量取消收藏视图"""

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
        return [self.uncollect_all_button, self.uncollect_selected_button]

    async def _confirm_uncollect_all(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """确认取消全部收藏的回调"""
        # Re-fetch all thread IDs
        all_threads, _ = await self.fetch_data_func(1, 9999)
        thread_ids = [t.thread_id for t in all_threads]

        if not thread_ids:
            await interaction.response.edit_message(
                content="没有帖子可以取消收藏。", view=None
            )
            return

        async with self.cog.get_session() as session:
            collection_service = CollectionService(session)
            result = await collection_service.remove_collections(
                interaction.user.id, CollectionType.THREAD, thread_ids
            )

            if result.removed_count > 0:
                thread_service = ThreadService(session)
                await thread_service.update_collection_counts(result.removed_ids, -1)

            await interaction.response.edit_message(
                content=f"操作完成！成功取消收藏 {result.removed_count} 个帖子。",
                view=None,
            )

        # Refresh the main view
        await self.update_data()
        await self.update_view(self.original_interaction)
        # 刷新主搜索视图
        if self.refresh_callback:
            await self.refresh_callback()

    @discord.ui.button(
        label="取消全部收藏",
        row=1,
        style=discord.ButtonStyle.danger,
        custom_id="uncollect_all",
    )
    async def uncollect_all_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        confirm_view = ConfirmationView(self._confirm_uncollect_all)
        await interaction.response.send_message(
            "⚠️ 您确定要取消收藏**所有**帖子吗？此操作无法撤销。",
            view=confirm_view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="取消选中收藏",
        row=1,
        style=discord.ButtonStyle.primary,
        custom_id="uncollect_selected",
    )
    async def uncollect_selected_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not self.selected_threads:
            await interaction.response.send_message(
                "请先选择帖子。", ephemeral=True, delete_after=10
            )
            return

        thread_ids = [int(tid) for tid in self.selected_threads]
        async with self.cog.get_session() as session:
            collection_service = CollectionService(session)
            result = await collection_service.remove_collections(
                interaction.user.id, CollectionType.THREAD, thread_ids
            )

            if result.removed_count > 0:
                thread_service = ThreadService(session)
                await thread_service.update_collection_counts(result.removed_ids, -1)

            await interaction.response.send_message(
                f"操作完成！成功取消收藏 {result.removed_count} 个帖子。",
                ephemeral=True,
                delete_after=10,
            )

        # 清空选择并刷新
        self.selected_threads.clear()
        await self.update_data()
        await self.update_view(interaction)
        # 刷新主搜索视图
        if self.refresh_callback:
            await self.refresh_callback()
