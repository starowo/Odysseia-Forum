from typing import TYPE_CHECKING, List

import discord

from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from preferences.preferences_service import PreferencesService
    from preferences.views.preferences_view import PreferencesView
    from search.dto.user_search_preferences import UserSearchPreferencesDTO


class ChannelPreferencesView(discord.ui.View):
    """用于设置用户默认搜索频道的独立视图"""

    def __init__(
        self,
        handler: "PreferencesService",
        original_interaction: discord.Interaction,
        parent_view: "PreferencesView",
        prefs_dto: "UserSearchPreferencesDTO",
        indexed_channels: List[discord.ForumChannel],
    ):
        super().__init__(timeout=300)  # 5分钟超时
        self.handler = handler
        self.original_interaction = original_interaction
        self.parent_view = parent_view
        self.prefs_dto = prefs_dto
        self.indexed_channels = indexed_channels

        preselected_ids = set(prefs_dto.preferred_channels or [])

        # 构建选项，只使用已索引的频道
        options = [
            discord.SelectOption(
                label=ch.name,
                value=str(ch.id),
                default=ch.id in preselected_ids,
            )
            for ch in self.indexed_channels[:25]  # 最多25个选项
        ]

        # 如果没有任何已索引的频道
        if not options:
            options.append(
                discord.SelectOption(
                    label="没有可用的已索引频道", value="disabled", default=False
                )
            )

        self.channel_select = discord.ui.Select(
            placeholder="选择你常用的搜索频道...",
            min_values=0,
            max_values=len(options) if options[0].value != "disabled" else 0,
            options=options,
            custom_id="channel_prefs_select",
            disabled=not self.indexed_channels,  # 如果没有频道则禁用
        )
        self.channel_select.callback = self.on_channel_select
        self.add_item(self.channel_select)

        self.save_button = discord.ui.Button(
            label="💾 保存设置",
            style=discord.ButtonStyle.success,
            custom_id="channel_prefs_save",
            disabled=not self.indexed_channels,  # 如果没有频道则禁用
        )
        self.save_button.callback = self.save_callback
        self.add_item(self.save_button)

    async def on_channel_select(self, interaction: discord.Interaction):
        """当用户在下拉菜单中做出选择时调用。"""
        # 更新选项的默认状态以保持选择
        selected_values = self.channel_select.values
        for option in self.channel_select.options:
            option.default = option.value in selected_values

        # 响应交互以防止超时并刷新视图
        await interaction.response.edit_message(view=self)

    async def start(self):
        """发送包含此视图的消息"""
        embed = discord.Embed(
            title="🔍 设置默认搜索频道",
            description="请选择在全局搜索时默认搜索的频道\n选择后，点击“保存设置”",
            color=0x3498DB,
        )

        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: self.original_interaction.followup.send(
                embed=embed, view=self, ephemeral=True
            ),
            priority=1,
        )

    async def save_callback(self, interaction: discord.Interaction):
        """保存按钮的回调"""
        await safe_defer(interaction, ephemeral=True)

        selected_channel_ids = [int(value) for value in self.channel_select.values]

        # 调用 handler 保存
        await self.handler.save_preferred_channels(
            interaction.user.id, selected_channel_ids
        )

        # 删除此临时设置消息
        await interaction.delete_original_response()

        # 刷新主偏好设置面板
        await self.parent_view.refresh(self.original_interaction)
