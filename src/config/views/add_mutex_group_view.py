import discord
from typing import List, TYPE_CHECKING, Optional
import logging

from shared.safe_defer import safe_defer
from .components.tag_page_button import TagPageButton

if TYPE_CHECKING:
    from ..mutex_tags_handler import MutexTagsHandler

logger = logging.getLogger(__name__)


class AddMutexGroupView(discord.ui.View):
    """
    一个专门用于新增互斥标签组的视图。
    这个视图会作为一个新的私密消息发送给用户。
    """
    def __init__(
        self,
        handler: "MutexTagsHandler",
        all_tag_names: List[str],
        father_interaction: discord.Interaction,
        step: int = 1,
        selected_priority_tags: Optional[List[str]] = None,
    ):
        super().__init__(timeout=900)
        self.handler = handler
        self.all_tag_names = sorted(all_tag_names)
        self.father_interaction: discord.Interaction = father_interaction
        self.step = step

        # UI 状态
        self.tag_page = 0
        self.tags_per_page = 25
        # 步骤1中选择的标签
        initial_tags = selected_priority_tags or []
        self.selected_tags: List[str] = (initial_tags + ["", "", "", ""])[:4]
        # 步骤2中选择的覆盖标签
        self.selected_override_tag: str = ""

        self.update_components()

    def update_components(self):
        """根据当前步骤和状态更新视图组件"""
        self.clear_items()

        if self.step == 1:
            self.add_priority_selectors()
            self.add_step1_buttons()
        elif self.step == 2:
            self.add_override_selector()
            self.add_step2_buttons()

        if len(self.all_tag_names) > self.tags_per_page:
            self.add_pagination_buttons()

    def add_priority_selectors(self):
        self.add_item(self.create_tag_select("优先级1 (最高)", 0))
        self.add_item(self.create_tag_select("优先级2", 1))
        self.add_item(self.create_tag_select("优先级3", 2))
        self.add_item(self.create_tag_select("优先级4", 3))

    def add_override_selector(self):
        self.add_item(self.create_override_tag_select())

    def add_step1_buttons(self):
        next_button = discord.ui.Button(
            label="➡️ 下一步", style=discord.ButtonStyle.primary, row=4
        )
        next_button.callback = self.on_next_button_click
        self.add_item(next_button)

        cancel_button = discord.ui.Button(
            label="❌ 取消", style=discord.ButtonStyle.secondary, row=4
        )
        cancel_button.callback = self.on_cancel_button_click
        self.add_item(cancel_button)

    def add_step2_buttons(self):
        save_button = discord.ui.Button(
            label="💾 保存", style=discord.ButtonStyle.success, row=4
        )
        save_button.callback = self.on_save_button_click
        self.add_item(save_button)

        back_button = discord.ui.Button(label="⬅️ 上一步", style=discord.ButtonStyle.secondary, row=4)
        back_button.callback = self.on_back_button_click
        self.add_item(back_button)

        cancel_button = discord.ui.Button(
            label="❌ 取消", style=discord.ButtonStyle.secondary, row=4
        )
        cancel_button.callback = self.on_cancel_button_click
        self.add_item(cancel_button)

    def add_pagination_buttons(self):
        max_page = (len(self.all_tag_names) - 1) // self.tags_per_page
        row = 4 if self.step == 1 else 1  # 根据步骤调整翻页按钮行号
        self.add_item(
            TagPageButton(
                "prev", self.on_tag_page_change, row=row, disabled=(self.tag_page == 0)
            )
        )
        self.add_item(
            TagPageButton(
                "next",
                self.on_tag_page_change,
                row=row,
                disabled=(self.tag_page >= max_page),
            )
        )

    def build_embed(self) -> discord.Embed:
        if self.step == 1:
            return self.build_step1_embed()
        else:  # step == 2
            return self.build_step2_embed()

    def build_step1_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="新增互斥标签组 (步骤 1/2)",
            description="请选择要添加到新互斥组的标签（按优先级从高到低）：",
            color=discord.Color.blue(),
        )
        selected_tags_str = []
        for i, tag in enumerate(self.selected_tags):
            if tag:
                selected_tags_str.append(f"优先级{i + 1}: `{tag}`")

        if selected_tags_str:
            embed.add_field(
                name="已选标签", value="\n".join(selected_tags_str), inline=False
            )
        else:
            embed.add_field(name="已选标签", value="无", inline=False)

        if len(self.all_tag_names) > self.tags_per_page:
            embed.set_footer(
                text=f"当前页: {self.tag_page + 1}/{(len(self.all_tag_names) - 1) // self.tags_per_page + 1}"
            )
        return embed

    def build_step2_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="新增互斥标签组 (步骤 2/2)",
            description="(可选) 设置一个**覆盖标签**。\n"
            "当检测到冲突时，如果此标签在频道中可用，将应用覆盖标签，并移除互斥组中的标签。",
            color=discord.Color.purple(),
        )
        priority_str = " ➡️ ".join(f"`{tag}`" for tag in self.selected_tags if tag)
        embed.add_field(name="已选优先级", value=priority_str, inline=False)

        override_display = (
            f"`{self.selected_override_tag}`"
            if self.selected_override_tag
            else "未设置"
        )
        embed.add_field(name="当前选择的覆盖标签", value=override_display, inline=False)
        return embed

    def create_tag_select(self, placeholder: str, priority_index: int):
        """创建一个分页的标签选择下拉菜单"""
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
            options=options
            if options
            else [discord.SelectOption(label="无可用标签", value="no_tags")],
            min_values=0,  # 允许不选择
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
            await interaction.edit_original_response(
                embed=self.build_embed(), view=self
            )

        select.callback = select_callback
        return select

    def create_override_tag_select(self):
        """创建用于选择覆盖标签的下拉菜单"""
        start_idx = self.tag_page * self.tags_per_page
        end_idx = start_idx + self.tags_per_page
        current_page_tags = self.all_tag_names[start_idx:end_idx]

        options = [
            discord.SelectOption(label=tag_name, value=tag_name)
            for tag_name in current_page_tags
        ]

        # 预设当前已选值
        current_selection = self.selected_override_tag
        for option in options:
            if option.value == current_selection:
                option.default = True

        placeholder_text = f"选择覆盖标签 (第 {self.tag_page + 1} 页)"

        select = discord.ui.Select(
            placeholder=placeholder_text,
            options=options
            if options
            else [discord.SelectOption(label="无可用标签", value="no_tags")],
            min_values=0,  # 允许不选择
            max_values=1,
            custom_id="override_tag_select",
            disabled=not options,
            row=0,
        )

        async def select_callback(interaction: discord.Interaction):
            await safe_defer(interaction)
            selected_value = select.values[0] if select.values else ""
            self.selected_override_tag = selected_value

            self.update_components()
            await interaction.edit_original_response(
                embed=self.build_embed(), view=self
            )

        select.callback = select_callback
        return select

    async def on_tag_page_change(self, interaction: discord.Interaction, action: str):
        """处理标签选择器的翻页请求"""
        await safe_defer(interaction)
        max_page = (len(self.all_tag_names) - 1) // self.tags_per_page
        if action == "prev":
            self.tag_page = max(0, self.tag_page - 1)
        elif action == "next":
            self.tag_page = min(max_page, self.tag_page + 1)

        self.update_components()
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.edit_original_response(
                embed=self.build_embed(), view=self
            ),
            priority=1,
        )

    async def on_next_button_click(self, interaction: discord.Interaction):
        """处理下一步按钮点击事件"""
        await self.handler.handle_add_group_step2(interaction, self)

    async def on_back_button_click(self, interaction: discord.Interaction):
        """处理返回上一步按钮点击事件。"""
        await self.handler.handle_back_to_step1(interaction, self)

    async def on_save_button_click(self, interaction: discord.Interaction):
        """处理保存按钮点击事件"""
        await self.handler.handle_save_new_group(interaction, self)

    async def on_cancel_button_click(self, interaction: discord.Interaction):
        """处理取消按钮点击事件，即安全地删除此消息"""
        await safe_defer(interaction)
        # 删除当前视图
        await self.handler.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.delete_original_response(),
            priority=1,
        )
