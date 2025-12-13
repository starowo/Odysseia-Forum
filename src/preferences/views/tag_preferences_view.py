from typing import TYPE_CHECKING, List, Set

import discord

from search.dto.user_search_preferences import UserSearchPreferencesDTO
from search.views.components.tag_page_button import TagPageButton
from shared.safe_defer import safe_defer
from shared.views.tag_select import TagSelect

if TYPE_CHECKING:
    from preferences.preferences_service import PreferencesService
    from preferences.views.preferences_view import PreferencesView


class TagPreferencesView(discord.ui.View):
    """用于管理用户标签偏好的视图。"""

    def __init__(
        self,
        handler: "PreferencesService",
        interaction: discord.Interaction,
        parent_view: "PreferencesView",
        preferences: "UserSearchPreferencesDTO",
        all_tags: List[str],
    ):
        super().__init__(timeout=900)
        self.handler = handler
        self.interaction = interaction
        self.parent_view = parent_view
        self.all_tags = all_tags

        # 将数据库中的列表转换为集合，以便于操作
        self.include_tags: Set[str] = set(preferences.include_tags or [])
        self.exclude_tags: Set[str] = set(preferences.exclude_tags or [])

        # UI 状态
        self.tag_page = 0
        self.tags_per_page = 25

        self.update_components()

    def update_components(self):
        """清除并重新添加所有UI组件。"""
        self.clear_items()

        # 添加标签选择器
        self.add_item(
            TagSelect(
                all_tags=self.all_tags,
                selected_tags=self.include_tags,
                page=self.tag_page,
                tags_per_page=self.tags_per_page,
                placeholder_prefix="正选",
                custom_id="prefs_include_tags",
                on_change_callback=self.on_include_tags_change,
                row=0,
            )
        )
        self.add_item(
            TagSelect(
                all_tags=self.all_tags,
                selected_tags=self.exclude_tags,
                page=self.tag_page,
                tags_per_page=self.tags_per_page,
                placeholder_prefix="反选",
                custom_id="prefs_exclude_tags",
                on_change_callback=self.on_exclude_tags_change,
                row=1,
            )
        )

        # 添加翻页按钮（如果需要）
        if len(self.all_tags) > self.tags_per_page:
            max_page = (len(self.all_tags) - 1) // self.tags_per_page
            self.add_item(
                TagPageButton(
                    "prev",
                    self.on_tag_page_change,
                    row=2,
                    disabled=(self.tag_page == 0),
                )
            )
            self.add_item(
                TagPageButton(
                    "next",
                    self.on_tag_page_change,
                    row=2,
                    disabled=(self.tag_page >= max_page),
                )
            )

        # 添加保存和取消按钮
        self.add_item(
            discord.ui.Button(
                label="保存", style=discord.ButtonStyle.green, custom_id="save", row=3
            )
        )
        self.add_item(
            discord.ui.Button(
                label="关闭", style=discord.ButtonStyle.grey, custom_id="cancel", row=3
            )
        )

        # 绑定回调
        self.children[-2].callback = self.save_preferences
        self.children[-1].callback = self.cancel_view

    async def start(self):
        """发送包含视图的初始消息。"""
        embed = self.build_embed()
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: self.interaction.followup.send(
                embed=embed, view=self, ephemeral=True
            ),
            priority=1,
        )

    def build_embed(self) -> discord.Embed:
        """构建显示当前偏好的Embed。"""
        embed = discord.Embed(title="标签偏好设置", color=discord.Color.blue())

        include_tags_str = ", ".join(sorted(list(self.include_tags))) or "无"
        exclude_tags_str = ", ".join(sorted(list(self.exclude_tags))) or "无"

        embed.add_field(
            name="✅ 正选标签", value=f"```{include_tags_str}```", inline=False
        )
        embed.add_field(
            name="❌ 反选标签", value=f"```{exclude_tags_str}```", inline=False
        )

        embed.set_footer(text="使用下面的下拉菜单修改设置，完成后请点击保存。")
        return embed

    async def on_include_tags_change(
        self, interaction: discord.Interaction, new_selection: Set[str]
    ):
        self.include_tags = new_selection
        await self.refresh_view(interaction)

    async def on_exclude_tags_change(
        self, interaction: discord.Interaction, new_selection: Set[str]
    ):
        self.exclude_tags = new_selection
        await self.refresh_view(interaction)

    async def refresh_view(self, interaction: discord.Interaction):
        self.update_components()
        embed = self.build_embed()
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.response.edit_message(
                embed=embed, view=self
            ),
            priority=1,
        )

    async def on_tag_page_change(self, interaction: discord.Interaction, action: str):
        """处理标签翻页。"""
        max_page = (len(self.all_tags) - 1) // self.tags_per_page
        if action == "prev":
            self.tag_page = max(0, self.tag_page - 1)
        elif action == "next":
            self.tag_page = min(max_page, self.tag_page + 1)

        self.update_components()
        embed = self.build_embed()
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.response.edit_message(
                embed=embed, view=self
            ),
            priority=1,
        )

    async def save_preferences(self, interaction: discord.Interaction):
        """保存偏好，刷新父视图，然后关闭此视图。"""
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: safe_defer(interaction), priority=1
        )

        # 1. 保存偏好到数据库
        await self.handler.save_tag_preferences(
            interaction, list(self.include_tags), list(self.exclude_tags)
        )

        # 2. 删除当前的标签偏好视图消息
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.delete_original_response(),
            priority=2,
        )

        # 3. 刷新父视图 (PreferencesView)，使用创建本视图的交互
        await self.parent_view.refresh(self.interaction)

    async def cancel_view(self, interaction: discord.Interaction):
        """取消操作，删除此视图"""
        await safe_defer(interaction)

        # 删除当前视图
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.delete_original_response(),
            priority=1,
        )

        # # 刷新父视图
        # await self.parent_view.refresh(self.interaction)
