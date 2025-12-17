import logging
from typing import TYPE_CHECKING, Optional

import discord

from preferences.preferences_repository import PreferencesRepository
from preferences.views.components.results_per_page_modal import ResultsPerPageModal
from search.constants import SortMethod
from search.dto.user_search_preferences import UserSearchPreferencesDTO
from search.views.components.keyword_modal import KeywordModal
from search.views.components.sort_method_select import SortMethodSelect
from shared.enum.default_preferences import DefaultPreferences
from shared.safe_defer import safe_defer
from shared.views.components.time_range_modal import TimeRangeModal

if TYPE_CHECKING:
    from preferences.preferences_service import PreferencesService

logger = logging.getLogger(__name__)


class PreferencesView(discord.ui.View):
    """统一的搜索偏好设置面板"""

    def __init__(
        self,
        service: "PreferencesService",
        interaction: discord.Interaction,
    ):
        super().__init__(timeout=890)  # 15分钟超时
        self.service = service
        self.original_interaction = interaction
        self.preferences: Optional[UserSearchPreferencesDTO] = None

    async def fetch_preferences(self) -> "UserSearchPreferencesDTO":
        """获取最新的用户偏好设置"""
        async with self.service.session_factory() as session:
            repo = PreferencesRepository(session, self.service.tag_service)
            prefs_dto = await repo.get_user_preferences(
                self.original_interaction.user.id
            )
            if not prefs_dto:
                # 创建一个临时的空DTO对象
                prefs_dto = UserSearchPreferencesDTO(
                    user_id=self.original_interaction.user.id
                )
            self.preferences = prefs_dto
            return prefs_dto

    def build_embed(self) -> discord.Embed:
        """构建显示当前偏好设置的Embed"""
        embed = discord.Embed(title="🔍 搜索偏好设置", color=0x3498DB)
        prefs = self.preferences

        if not prefs:
            embed.description = "正在加载偏好设置..."
            return embed

        # 标签偏好
        tag_info = []
        if prefs.include_tags:
            tag_info.append(f"**✅ 正选标签：** {', '.join(prefs.include_tags)}")
        if prefs.exclude_tags:
            tag_info.append(f"**❌ 反选标签：** {', '.join(prefs.exclude_tags)}")
        if tag_info:
            embed.add_field(
                name="🏷️ 标签设置",
                value="\n".join(tag_info),
                inline=False,
            )

        # 关键词偏好
        keyword_info = []
        if prefs.include_keywords:
            keyword_info.append(f"**✅ 包含关键词：** {prefs.include_keywords}")
        if prefs.exclude_keywords:
            keyword_info.append(f"**❌ 排除关键词：** {prefs.exclude_keywords}")
        if (
            prefs.exclude_keyword_exemption_markers
            and prefs.exclude_keyword_exemption_markers != ["禁", "🈲"]
        ):
            markers_str = ", ".join(prefs.exclude_keyword_exemption_markers)
            keyword_info.append(f"**豁免标记：** {markers_str}")

        if keyword_info:
            embed.add_field(
                name="📝 关键词设置",
                value="\n".join(keyword_info),
                inline=False,
            )

        # 频道偏好
        channel_names = []
        if prefs.preferred_channels and self.original_interaction.guild:
            for channel_id in prefs.preferred_channels:
                channel = self.original_interaction.guild.get_channel(channel_id)
                if channel:
                    channel_names.append(channel.mention)

        if channel_names:
            embed.add_field(
                name="🔍 偏好频道",
                value=", ".join(channel_names),
                inline=False,
            )

        # 时间偏好
        time_info = []
        if prefs.created_after:
            time_info.append(f"**发帖晚于:** {prefs.created_after}")
        if prefs.created_before:
            time_info.append(f"**发帖早于:** {prefs.created_before}")
        if prefs.active_after:
            time_info.append(f"**活跃晚于:** {prefs.active_after}")
        if prefs.active_before:
            time_info.append(f"**活跃早于:** {prefs.active_before}")

        if time_info:
            embed.add_field(name="⏱️ 时间设置", value="\n".join(time_info), inline=False)

        # 预览图设置
        current_preview_mode = (
            prefs.preview_image_mode
            if prefs and prefs.preview_image_mode
            else DefaultPreferences.PREVIEW_IMAGE_MODE.value
        )
        preview_display = (
            "大图（下方大图）"
            if current_preview_mode == "image"
            else "缩略图（右侧小图）"
        )
        embed.add_field(
            name="🖼️ 预览图显示方式",
            value=f"{preview_display}",
            inline=True,
        )

        # 每页数量
        current_results_per_page = (
            prefs.results_per_page
            if prefs and prefs.results_per_page
            else DefaultPreferences.RESULTS_PER_PAGE.value
        )
        embed.add_field(
            name="📊 每页显示结果数",
            value=f"   {current_results_per_page}",
            inline=True,
        )

        # 排序偏好
        current_sort_method = (
            prefs.sort_method
            if prefs and prefs.sort_method
            else DefaultPreferences.SORT_METHOD.value
        )
        sort_method_display = SortMethod.get_label_by_value(current_sort_method, "未知")

        # 如果为自定义排序，则附加显示基础算法
        if current_sort_method == "custom":
            current_base_sort = (
                prefs.custom_base_sort
                if prefs and prefs.custom_base_sort
                else DefaultPreferences.SORT_METHOD.value
            )
            base_sort_display = SortMethod.get_label_by_value(current_base_sort, "未知")
            sort_method_display += f" (基础: {base_sort_display})"

        embed.add_field(
            name="🔀 排序算法",
            value=f"{sort_method_display}",
            inline=False,
        )

        # 作者偏好
        author_info = []
        if prefs.include_authors:
            author_info.append(
                f"✅ 包含作者： {', '.join([f'<@{author_id}>' for author_id in prefs.include_authors])}"
            )
        if prefs.exclude_authors:
            author_info.append(
                f"❌ 排除作者： {', '.join([f'<@{author_id}>' for author_id in prefs.exclude_authors])}"
            )
        if author_info:
            embed.add_field(
                name="👤 作者设置",
                value="\n".join(author_info),
                inline=False,
            )

        return embed

    def update_components(self):
        """根据当前状态更新组件（主要是预览图按钮）"""
        self.clear_items()

        # --- 第一行: 主排序算法 ---
        current_sort_method = (
            self.preferences.sort_method
            if self.preferences and self.preferences.sort_method
            else DefaultPreferences.SORT_METHOD.value
        )
        self.add_item(
            SortMethodSelect(
                current_sort=current_sort_method,
                update_callback=self.handle_sort_method_change,
                row=0,
            )
        )

        # --- 第二行: 基础排序算法 (条件性显示) ---
        if current_sort_method == "custom":
            current_base_sort = (
                self.preferences.custom_base_sort
                if self.preferences and self.preferences.custom_base_sort
                else DefaultPreferences.SORT_METHOD.value
            )
            self.add_item(
                SortMethodSelect(
                    current_sort=current_base_sort,
                    update_callback=self.handle_base_sort_change,
                    row=1,
                    exclude_values=["custom"],  # 排除自定义选项
                    placeholder="选择自定义搜索的基础排序算法...",
                )
            )

        # 第三行
        self.add_item(
            discord.ui.Button(
                label="🏷️ 标签",
                style=discord.ButtonStyle.secondary,
                custom_id="prefs_tags",
                row=2,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="📝 关键词",
                style=discord.ButtonStyle.secondary,
                custom_id="prefs_keywords",
                row=2,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="🔍 频道",
                style=discord.ButtonStyle.secondary,
                custom_id="prefs_channels",
                row=2,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="⏱️ 时间",
                style=discord.ButtonStyle.secondary,
                custom_id="prefs_time",
                row=2,
            )
        )

        # 第四行
        current_preview_mode = (
            self.preferences.preview_image_mode
            if self.preferences and self.preferences.preview_image_mode
            else DefaultPreferences.PREVIEW_IMAGE_MODE.value
        )
        preview_button_label = (
            "🔄 切换为缩略图" if current_preview_mode == "image" else "🔄 切换为大图"
        )
        self.add_item(
            discord.ui.Button(
                label=preview_button_label,
                style=discord.ButtonStyle.secondary,
                custom_id="prefs_preview",
                row=3,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="📊 每页结果数",
                style=discord.ButtonStyle.secondary,
                custom_id="prefs_page_size",
                row=3,
            )
        )

        # 第五行
        self.add_item(
            discord.ui.Button(
                label="🗑️ 清空所有设置",
                style=discord.ButtonStyle.danger,
                custom_id="prefs_clear",
                row=4,
            )
        )

        # 绑定回调
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.callback = self.button_callback

    async def start(self):
        """发送包含视图的初始消息"""
        await self.fetch_preferences()
        self.update_components()
        embed = self.build_embed()
        await self.service.bot.api_scheduler.submit(
            coro_factory=lambda: self.original_interaction.followup.send(
                embed=embed, view=self, ephemeral=True
            ),
            priority=1,
        )

    async def refresh(self, interaction: discord.Interaction):
        """
        使用最新的偏好设置刷新视图。
        """
        await self.fetch_preferences()
        self.update_components()
        embed = self.build_embed()
        await self.service.bot.api_scheduler.submit(
            coro_factory=lambda: interaction.edit_original_response(
                embed=embed, view=self
            ),
            priority=1,
        )

    async def button_callback(self, interaction: discord.Interaction):
        """统一处理所有按钮点击事件"""
        assert interaction.data is not None
        custom_id = interaction.data.get("custom_id")

        if custom_id == "prefs_tags":
            await self.service.search_preferences_tags(interaction, self)
            return  # 标签视图是独立的流程

        elif custom_id == "prefs_keywords":
            # 获取当前偏好用于填充 Modal
            prefs = self.preferences  # 假设已经通过 fetch_preferences 获取
            initial_include = prefs.include_keywords if prefs else ""
            initial_exclude = prefs.exclude_keywords if prefs else ""
            initial_markers = (
                ", ".join(prefs.exclude_keyword_exemption_markers)
                if prefs and prefs.exclude_keyword_exemption_markers
                else ", ".join(DefaultPreferences.EXEMPTION_MARKERS.value)
            )

            # 创建并发送 Modal
            modal = KeywordModal(
                initial_keywords=initial_include,
                initial_exclude_keywords=initial_exclude,
                submit_callback=self.handle_keyword_modal_submit,
                initial_exemption_markers=initial_markers,
            )
            await interaction.response.send_modal(modal)
            return  # Modal 流程自己处理响应

        elif custom_id == "prefs_channels":
            await self.service.search_preferences_channels(interaction, self)
            return  # 服务自己处理响应

        elif custom_id == "prefs_time":
            initial_values = {
                "created_after": self.preferences.created_after
                if self.preferences
                else None,
                "created_before": self.preferences.created_before
                if self.preferences
                else None,
                "active_after": self.preferences.active_after
                if self.preferences
                else None,
                "active_before": self.preferences.active_before
                if self.preferences
                else None,
            }
            modal = TimeRangeModal(self.handle_prefs_time_modal_submit, initial_values)
            await interaction.response.send_modal(modal)
            return

        elif custom_id == "prefs_page_size":
            current_page_size = (
                self.preferences.results_per_page
                if self.preferences and self.preferences.results_per_page
                else 5  # 默认值
            )
            modal = ResultsPerPageModal(self.service, self, current_page_size)
            await self.service.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.response.send_modal(modal), priority=1
            )
            return  # Modal 流程自己处理响应

        elif custom_id == "prefs_preview":
            await safe_defer(interaction)
            await self.service.toggle_preview_mode(interaction.user.id)
            await self.refresh(interaction)
            return

        elif custom_id == "prefs_clear":
            await safe_defer(interaction)
            await self.service.clear_user_preferences(interaction.user.id)
            await self.refresh(interaction)
            return

    async def handle_keyword_modal_submit(
        self,
        modal_interaction: discord.Interaction,
        submitted_include: str,
        submitted_exclude: str,
        submitted_markers: str,
    ):
        await safe_defer(modal_interaction, ephemeral=True)
        try:
            await self.service.save_user_keywords(
                user_id=modal_interaction.user.id,
                include_str=submitted_include,
                exclude_str=submitted_exclude,
                exemption_markers_str=submitted_markers,
            )
            # 刷新本视图
            await self.refresh(modal_interaction)
        except Exception as e:
            logger.error(f"保存关键词偏好失败: {e}", exc_info=True)
            await modal_interaction.followup.send(f"❌ 保存失败: {e}", ephemeral=True)

    async def handle_sort_method_change(
        self, interaction: discord.Interaction, sort_method: str
    ):
        """处理主排序方式选择的回调"""
        await safe_defer(interaction)
        try:
            # 保存时，如果新方法不是 custom，可以考虑重置 base_sort
            update_data = {"sort_method": sort_method}
            if sort_method != "custom":
                update_data["custom_base_sort"] = "comprehensive"

            await self.service.save_user_preferences(interaction.user.id, update_data)
            await self.refresh(interaction)  # 刷新视图以显示或隐藏新行
        except Exception as e:
            logger.error(f"保存排序方式失败: {e}", exc_info=True)
            await interaction.followup.send(f"❌ 保存失败: {e}", ephemeral=True)

    # 处理基础排序算法变化的回调
    async def handle_base_sort_change(
        self, interaction: discord.Interaction, sort_method: str
    ):
        """处理基础排序方式选择的回调"""
        await safe_defer(interaction)
        try:
            # 注意这里 service 的方法是通用的，可以直接用
            await self.service.save_user_preferences(
                interaction.user.id, {"custom_base_sort": sort_method}
            )
            await self.refresh(interaction)  # 刷新视图以更新embed中的文本
        except Exception as e:
            logger.error(f"保存基础排序方式失败: {e}", exc_info=True)
            await interaction.followup.send(f"❌ 保存失败: {e}", ephemeral=True)

    async def handle_prefs_time_modal_submit(
        self, interaction: discord.Interaction, values: dict
    ):
        """回调：接收原始字符串并调用服务进行保存。"""
        await safe_defer(interaction)
        try:
            await self.service.save_time_preferences(interaction.user.id, values)
            await self.refresh(interaction)
        except Exception as e:
            logger.error(f"保存时间偏好失败: {e}", exc_info=True)
            await interaction.followup.send(f"❌ 保存失败: {e}", ephemeral=True)
