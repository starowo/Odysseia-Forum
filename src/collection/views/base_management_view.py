import discord
from typing import TYPE_CHECKING, List, Optional, Callable, Awaitable, Tuple, Set

from shared.models import Thread
from shared.safe_defer import safe_defer
from shared.views.components.page_jump_modal import PageJumpModal

if TYPE_CHECKING:
    from ..cog import CollectionCog


class BaseManagementView(discord.ui.View):
    """批量管理视图的基类，处理通用分页和UI更新逻辑"""

    def __init__(
        self,
        cog: "CollectionCog",
        interaction: discord.Interaction,
        title: str,
        fetch_data_func: Callable[[int, int], Awaitable[Tuple[List[Thread], int]]],
        refresh_callback: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        super().__init__(timeout=300)
        self.cog = cog
        self.original_interaction = interaction
        self.title = title
        self.fetch_data_func = fetch_data_func
        self.refresh_callback = refresh_callback

        self.page = 1
        self.per_page = 25
        self.total_items = 0
        self.max_page = 1
        self.threads: List[Thread] = []
        self.selected_threads: Set[str] = set()
        self.message: Optional[discord.WebhookMessage] = None
        self.thread_cache: dict[str, str] = {}

    async def start(self):
        """初始化并发送视图"""
        await self.update_data()
        await self.update_view(self.original_interaction)

    async def update_data(self):
        """获取最新数据并更新分页状态"""
        threads, self.total_items = await self.fetch_data_func(
            self.page,
            self.per_page,
        )
        self.threads = threads
        # 更新帖子标题缓存
        for thread in threads:
            self.thread_cache[str(thread.thread_id)] = thread.title
        self.max_page = (self.total_items + self.per_page - 1) // self.per_page or 1
        self.page = min(self.page, self.max_page)

    def build_embed(self) -> discord.Embed:
        """构建Embed"""
        if not self.threads:
            return discord.Embed(
                title=self.title,
                description="这里什么都没有。",
                color=discord.Color.orange(),
            )

        description_lines = []
        for idx, thread in enumerate(self.threads, start=1):
            url = f"https://discord.com/channels/{self.original_interaction.guild_id}/{thread.thread_id}"
            description_lines.append(f"{idx}. [{thread.title}]({url})")

        embed = discord.Embed(
            title=self.title,
            description="\n".join(description_lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(
            text=f"第 {self.page}/{self.max_page} 页 | 共 {self.total_items} 个帖子"
        )
        return embed

    def create_components(self) -> List[discord.ui.Item]:
        """创建UI组件"""
        raise NotImplementedError("Subclasses must implement create_components")

    async def update_view(self, interaction: discord.Interaction):
        """更新视图"""
        await safe_defer(interaction, ephemeral=True)
        self.clear_items()

        # 添加特定于子类的组件 (例如 Select 菜单)
        for item in self.create_components():
            self.add_item(item)

        # 添加操作按钮 (例如 收藏/取消收藏)
        for item in self.get_action_buttons():
            self.add_item(item)

        # 添加固定的分页按钮
        self.add_item(self.prev_page_button)
        self.add_item(self.page_jump_button)
        self.add_item(self.next_page_button)

        # 更新分页按钮状态
        self.prev_page_button.disabled = self.page <= 1
        self.next_page_button.disabled = self.page >= self.max_page

        self.page_jump_button.label = f"{self.page}/{self.max_page}"
        self.page_jump_button.style = (
            discord.ButtonStyle.primary
            if self.max_page > 1
            else discord.ButtonStyle.secondary
        )
        self.page_jump_button.disabled = self.max_page <= 1

        embeds_to_send = []

        # 添加主列表 embed
        main_embed = self.build_embed()
        embeds_to_send.append(main_embed)

        # 如果有选中的帖子，创建一个专门的 embed 来显示它们
        if self.selected_threads:
            selection_embed = self.build_selection_embed()
            embeds_to_send.append(selection_embed)

        if self.message:
            await self.message.edit(embeds=embeds_to_send, view=self)
        else:
            self.message = await interaction.followup.send(
                embeds=embeds_to_send, view=self, ephemeral=True, wait=True
            )

    def get_action_buttons(self) -> List[discord.ui.Item]:
        """获取特定视图的操作按钮"""
        return []

    def build_selection_embed(self) -> discord.Embed:
        """构建显示已选中帖子的 Embed"""

        selected_thread_lines = []
        guild_id = self.original_interaction.guild_id
        # 从缓存中获取标题
        for idx, thread_id in enumerate(sorted(list(self.selected_threads)), start=1):
            title = self.thread_cache.get(thread_id, f"帖子ID: {thread_id}")
            url = f"https://discord.com/channels/{guild_id}/{thread_id}"
            selected_thread_lines.append(
                f"{idx}. [{title[:80]}]({url})"
            )  # 避免描述过长

        description = "\n".join(selected_thread_lines)
        embed = discord.Embed(
            title=f"已选中 {len(self.selected_threads)} 个帖子",
            description=description,
            color=discord.Color.green(),
        )
        return embed

    async def on_timeout(self):
        if self.message:
            # 禁用所有组件
            for item in self.children:
                if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                    item.disabled = True
            await self.message.edit(view=self, content="视图已超时。")

    async def on_selected_threads_change(
        self, interaction: discord.Interaction, current_page_selection: Set[str]
    ):
        """当选中帖子发生变化时调用, 实现跨页累积选择"""

        # 移除本页所有帖子的当前选择状态
        current_page_thread_ids = {str(t.thread_id) for t in self.threads}
        self.selected_threads.difference_update(current_page_thread_ids)

        # 添加本页新的选择
        self.selected_threads.update(current_page_selection)

        await self.update_view(interaction)

    @discord.ui.button(
        label="⬅️ 上一页",
        custom_id="prev_page",
        row=2,
        style=discord.ButtonStyle.secondary,
    )
    async def prev_page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page > 1:
            self.page -= 1
            await self.update_data()
        await self.update_view(interaction)

    async def _handle_page_jump(self, interaction: discord.Interaction, page_num: int):
        """处理页面跳转的回调"""
        self.page = page_num
        await self.update_data()
        await self.update_view(interaction)

    @discord.ui.button(
        label="1/1", custom_id="page_jump", row=2, style=discord.ButtonStyle.primary
    )
    async def page_jump_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        modal = PageJumpModal(
            max_page=self.max_page, submit_callback=self._handle_page_jump
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="下一页 ➡️",
        custom_id="next_page",
        row=2,
        style=discord.ButtonStyle.secondary,
    )
    async def next_page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page < self.max_page:
            self.page += 1
            await self.update_data()
        await self.update_view(interaction)
