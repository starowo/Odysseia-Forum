import discord
from typing import List, TYPE_CHECKING
import logging

from shared.safe_defer import safe_defer
from shared.api_scheduler import APIScheduler
from .components.tag_page_button import TagPageButton

if TYPE_CHECKING:
    from ..mutex_tags_handler import MutexTagsHandler

logger = logging.getLogger(__name__)

class AddMutexGroupView(discord.ui.View):
    """
    一个专门用于新增互斥标签组的视图。
    这个视图会作为一个新的私密消息发送给用户。
    """
    def __init__(self, handler: "MutexTagsHandler", all_tag_names: List[str],father_interaction : discord.Interaction):
        super().__init__(timeout=600)
        self.handler = handler
        self.all_tag_names = sorted(all_tag_names)
        self.father_interaction : discord.Interaction = father_interaction
        
        # UI 状态
        self.tag_page = 0
        self.tags_per_page = 25
        self.selected_tags: List[str] = ["", "", "", ""] # 存储每个优先级选择器选中的标签
        
        self.update_components()

    def update_components(self):
        """根据当前状态更新视图中的所有组件。"""
        self.clear_items()
        
        # 添加标签选择器
        self.add_item(self.create_tag_select("优先级1 (最高)", 0))
        self.add_item(self.create_tag_select("优先级2", 1))
        self.add_item(self.create_tag_select("优先级3", 2))
        self.add_item(self.create_tag_select("优先级4", 3))

        # 添加保存和取消按钮
        save_button = discord.ui.Button(label="💾 保存", style=discord.ButtonStyle.success, row=4)
        save_button.callback = self.on_save_button_click
        self.add_item(save_button)
        
        # 添加翻页按钮（如果需要）
        if len(self.all_tag_names) > self.tags_per_page:
            max_page = (len(self.all_tag_names) - 1) // self.tags_per_page
            self.add_item(
                TagPageButton(
                    "prev", self.on_tag_page_change, row=4, disabled=(self.tag_page == 0)
                )
            )
            self.add_item(
                TagPageButton(
                    "next",
                    self.on_tag_page_change,
                    row=4,
                    disabled=(self.tag_page >= max_page),
                )
            )

        cancel_button = discord.ui.Button(label="❌ 取消", style=discord.ButtonStyle.secondary, row=4)
        cancel_button.callback = self.on_cancel_button_click
        self.add_item(cancel_button)

    def build_embed(self) -> discord.Embed:
        """构建显示当前选择标签的Embed。"""
        embed = discord.Embed(title="新增互斥标签组", description="请选择要添加到新互斥组的标签（按优先级从高到低）：", color=discord.Color.blue())
        
        selected_tags_str = []
        for i, tag in enumerate(self.selected_tags):
            if tag:
                selected_tags_str.append(f"优先级{i+1}: `{tag}`")
        
        if selected_tags_str:
            embed.add_field(name="已选标签", value="\n".join(selected_tags_str), inline=False)
        else:
            embed.add_field(name="已选标签", value="无", inline=False)
            
        embed.set_footer(text=f"当前页: {self.tag_page + 1}/{(len(self.all_tag_names) - 1) // self.tags_per_page + 1}")
        return embed

    def create_tag_select(self, placeholder: str, priority_index: int):
        """创建一个分页的标签选择下拉菜单。"""
        start_idx = self.tag_page * self.tags_per_page
        end_idx = start_idx + self.tags_per_page
        current_page_tags = self.all_tag_names[start_idx:end_idx]

        options = [
            discord.SelectOption(label=tag_name, value=tag_name)
            for tag_name in current_page_tags
        ]
        
        # 预设当前已选值
        current_selection = self.selected_tags[priority_index]
        for option in options:
            if option.value == current_selection:
                option.default = True

        placeholder_text = f"{placeholder} (第 {self.tag_page + 1} 页)"
        
        select = discord.ui.Select(
            placeholder=placeholder_text,
            options=options if options else [discord.SelectOption(label="无可用标签", value="no_tags")],
            min_values=0, # 允许不选择
            max_values=1,
            custom_id=f"tag_select_{priority_index}",
            disabled=not options,
            row=priority_index,
        )

        async def select_callback(interaction: discord.Interaction):
            await safe_defer(interaction)
            selected_value = select.values[0] if select.values else ""
            self.selected_tags[priority_index] = selected_value
            
            self.update_components()
            await interaction.edit_original_response(embed=self.build_embed(), view=self)

        select.callback = select_callback
        return select

    async def on_tag_page_change(self, interaction: discord.Interaction, action: str):
        """处理标签选择器的翻页请求。"""
        await safe_defer(interaction)
        max_page = (len(self.all_tag_names) - 1) // self.tags_per_page
        if action == "prev":
            self.tag_page = max(0, self.tag_page - 1)
        elif action == "next":
            self.tag_page = min(max_page, self.tag_page + 1)

        self.update_components()
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.edit_original_response(embed=self.build_embed(), view=self),
            priority=1,
        )

    async def on_save_button_click(self, interaction: discord.Interaction):
        """处理保存按钮点击事件。"""
        await self.handler.handle_save_new_group(interaction, self)

    async def on_cancel_button_click(self, interaction: discord.Interaction):
        """处理取消按钮点击事件，即安全地删除此消息。"""
        await safe_defer(interaction)
        
        # 删除当前视图
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.delete_original_response(),
            priority=1,
        )