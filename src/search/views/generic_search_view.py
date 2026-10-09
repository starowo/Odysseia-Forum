import re
from typing import TYPE_CHECKING, Optional, Set

import discord

from search.dto.search_state import SearchStateDTO
from search.qo.thread_search import ThreadSearchQuery
from search.strategies import (
    CollectionSearchStrategy,
    SearchStrategy,
)
from search.views.combined_search_view import CombinedSearchView
from search.views.custom_search_settings_view import CustomSearchSettingsView
from search.views.results_view import SearchResultsView
from search.components.keyword_modal import KeywordModal
from shared.enum import DefaultPreferences
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from search.cog import Search


class GenericSearchView(discord.ui.View):
    """筛选逻辑的核心视图，它操作一个 SearchStateDTO 来管理状态。"""

    def __init__(
        self,
        cog: "Search",
        interaction: discord.Interaction,
        search_state: SearchStateDTO,
        strategy: SearchStrategy,
    ):
        super().__init__(timeout=14400)  # 4 小时
        self.cog = cog
        self.last_interaction = interaction
        self.search_state = search_state
        self.strategy = strategy

        # --- UI状态 ---
        self.tags_per_page = 25
        self.last_search_results: dict | None = None
        self.custom_settings_message: Optional[discord.WebhookMessage] = None

        # 临时桥接变量，用来填补“主搜索视图刚弹出来，却在子视图里做了操作”这段真空期
        self.view_message: Optional[discord.WebhookMessage] = None

    async def start(self, send_new_ephemeral: bool = False):
        """
        初始化视图

        Args:
            send_new_ephemeral (bool): 如果为 True，则发送一个新的私密消息，而不是编辑原始消息
        """

        # 使用主服务器身份组刷新当前用户的深渊向候选权限。
        self.search_state.can_view_abyss_tags = self.cog.can_view_abyss_tags(
            self.last_interaction.user.id
        )

        # 填充可用的标签列表
        self.search_state.all_available_tags = await self.strategy.get_available_tags(
            self.cog, self.search_state
        )

        # 更新主搜索视图
        await self.update_view(
            self.last_interaction, send_new_ephemeral=send_new_ephemeral
        )

        # 检查是否需要立即弹出自定义设置视图
        if (
            self.search_state.sort_method == "custom"
            and self.custom_settings_message is None
        ):
            settings_view = CustomSearchSettingsView(self)

            self.custom_settings_message = await settings_view.start()

    async def update_view(
        self,
        interaction: discord.Interaction,
        rerun_search: bool = True,
        send_new_ephemeral: bool = False,
        from_subview: bool = False,
    ):
        """
        根据当前状态更新整个视图，包括UI组件和搜索结果

        Args:
            rerun_search (bool): 如果为 True，则根据恢复的状态重新执行一次搜索
            send_new_ephemeral (bool): 如果为 True，则发送一个新的私密消息，而不是编辑原始消息
            from_subview (bool): 如果为 True，表示由子视图触发，需要调用桥接逻辑
        """
        await safe_defer(interaction, ephemeral=True)

        results = {}
        if rerun_search:
            results = await self._execute_search(interaction)
            self.last_search_results = results
        elif self.last_search_results:
            results = self.last_search_results
        else:
            # Fallback: if no cache exists, must run search
            results = await self._execute_search(interaction)
            self.last_search_results = results

        # 准备所有UI组件
        filter_components = self.strategy.get_filter_components(self)

        # 构建消息和最终视图
        content = self.strategy.get_title()  # 使用策略获取标题

        if self.search_state.channel_ids and not isinstance(
            self.strategy, CollectionSearchStrategy
        ):
            channel_mentions = []
            for cid in self.search_state.channel_ids:
                # 尝试从 CacheService 获取频道对象（该缓存包含所有服务器的已索引频道）
                channel = self.cog.cache_service.indexed_channels.get(cid)
                if channel:
                    channel_mentions.append(channel.name)
                else:
                    # 即使缓存中没有（可能是极端同步延迟），使用标准的 Discord 提及语法也能显示
                    channel_mentions.append(f"<#{cid}>")

            if channel_mentions:
                content = f"在 **{', '.join(channel_mentions)}** 中搜索"

        thread_embeds = results.get("embeds", [])
        summary_embed = self.build_summary_embed(results)

        final_embeds_to_send = thread_embeds + [summary_embed]

        final_view = None
        if results.get("has_results"):
            # 如果有结果，创建分页视图并组合
            results_view = SearchResultsView(
                self.cog,
                interaction,
                self.build_query_object(),
                results["total"],
                results["page"],
                results["per_page"],
                self.update_view_from_pager,  # 使用新的回调
                self.search_state.results_per_page,
                self.search_state.preview_image_mode,
            )
            final_view = CombinedSearchView(self, results_view, filter_components)
        else:
            # 如果没有结果，只显示筛选器。
            # 重新创建一个只包含筛选组件的视图，避免状态污染。
            final_view = discord.ui.View(timeout=self.timeout)
            for item in filter_components:
                final_view.add_item(item)

        # 更新消息，按模式选择发送新消息或编辑已有消息
        if send_new_ephemeral:
            # 发送新私密消息，写入临时桥接变量
            async def _send_new():
                msg = await interaction.followup.send(
                    content=content,
                    view=final_view,
                    embeds=final_embeds_to_send,
                    ephemeral=True,
                    wait=True,
                )
                self.view_message = msg

            await self.cog.bot.api_scheduler.submit(coro_factory=_send_new, priority=1)

        elif not from_subview:
            # 视图自身触发的刷新，更新交互
            self.last_interaction = interaction
            self.view_message = None

            edit_coro = interaction.edit_original_response(
                content=content, view=final_view, embeds=final_embeds_to_send
            )
            await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: edit_coro, priority=1
            )
        else:
            # 自定义设置视图 (子视图) 触发的刷新
            if self.view_message is not None:
                edit_coro = self.view_message.edit(
                    content=content, view=final_view, embeds=final_embeds_to_send
                )
            else:
                edit_coro = self.last_interaction.edit_original_response(
                    content=content, view=final_view, embeds=final_embeds_to_send
                )
            await self.cog.bot.api_scheduler.submit(
                coro_factory=lambda: edit_coro, priority=1
            )

    async def _execute_search(self, interaction: discord.Interaction) -> dict:
        """执行搜索并返回结果"""
        state = self.search_state
        search_qo = self.build_query_object()

        # 从 self.search_state 中获取显示参数
        results = await self.cog.search_and_display(
            interaction=interaction,
            search_qo=search_qo,
            page=state.page,
            per_page=state.results_per_page,  # 传递每页数量
            preview_mode=state.preview_image_mode,  # 传递预览模式
        )
        return results

    async def update_view_from_pager(
        self,
        interaction: discord.Interaction,
        page: int,
        per_page: int,
        preview_mode: str,
    ):
        """由分页视图 (SearchResultsView) 调用的回调"""
        self.search_state.page = page
        self.search_state.results_per_page = per_page
        self.search_state.preview_image_mode = preview_mode
        await self.update_view(interaction, rerun_search=True)

    async def on_filter_change(self, interaction: discord.Interaction):
        """当任何筛选条件改变时调用此方法，设置最后交互，重置页码并重新搜索"""
        self.last_interaction = interaction
        self.search_state.page = 1
        await self.update_view(interaction, rerun_search=True)

    async def on_sort_order_change(self, interaction: discord.Interaction):
        """排序正/倒序切换"""
        self.search_state.sort_order = (
            "asc" if self.search_state.sort_order == "desc" else "desc"
        )
        await self.on_filter_change(interaction)

    async def on_tag_logic_change(self, interaction: discord.Interaction):
        """标签匹配部分匹配/全部匹配切换"""
        self.search_state.tag_logic = (
            "or" if self.search_state.tag_logic == "and" else "and"
        )
        await self.on_filter_change(interaction)

    async def on_sort_method_change(
        self, interaction: discord.Interaction, new_method: str
    ):
        """排序算法切换"""
        # 清理可能存在的旧配置视图
        if self.custom_settings_message:
            try:
                await self.custom_settings_message.delete()
            except (discord.errors.NotFound, discord.errors.HTTPException):
                pass  # 消息可能已被删除，忽略错误
            finally:
                self.custom_settings_message = None

        self.search_state.sort_method = new_method

        if new_method == "custom":
            # 更新主视图以反映标签变化，但不重新搜索
            await self.update_view(interaction, rerun_search=False)

            # 弹出自定义设置视图
            settings_view = CustomSearchSettingsView(self)
            self.custom_settings_message = await settings_view.start()

            return

        await self.on_filter_change(interaction)

    async def trigger_search_from_custom_settings(
        self, updated_state: "SearchStateDTO"
    ):
        """由 CustomSearchSettingsView 回调，应用设置并刷新主视图"""
        self.search_state = updated_state
        self.search_state.page = 1
        await self.update_view(
            self.last_interaction, rerun_search=True, from_subview=True
        )

    async def on_tag_page_change(self, interaction: discord.Interaction, action: str):
        """处理标签翻页"""
        max_page = (len(self.search_state.all_available_tags) - 1) // self.tags_per_page
        if action == "prev":
            self.search_state.tag_page = max(0, self.search_state.tag_page - 1)
        elif action == "next":
            self.search_state.tag_page = min(max_page, self.search_state.tag_page + 1)

        # 标签翻页只需更新视图，不需要重新搜索
        await self.update_view(interaction, rerun_search=False)

    async def handle_keyword_update(
        self,
        interaction: discord.Interaction,
        keywords: str,
        exclude_keywords: str,
        exemption_markers: str,
    ):
        """处理来自KeywordModal的数据回传"""

        self.search_state.keywords = keywords
        self.search_state.exclude_keywords = exclude_keywords
        self.search_state.exemption_markers = sorted(
            list(
                {
                    p.strip()
                    for p in re.split(r"[，,/\s]+", exemption_markers)
                    if p.strip()
                }
            )
        )
        await self.on_filter_change(interaction)

    async def show_keyword_modal(self, interaction: discord.Interaction):
        """创建并显示 KeywordModal"""
        modal = KeywordModal(
            initial_keywords=self.search_state.keywords,
            initial_exclude_keywords=self.search_state.exclude_keywords,
            initial_exemption_markers=", ".join(self.search_state.exemption_markers),
            submit_callback=self.handle_keyword_update,
        )
        await interaction.response.send_modal(modal)

    async def on_include_tags_change(
        self, interaction: discord.Interaction, new_selection: Set[str]
    ):
        self.search_state.include_tags = new_selection
        await self.on_filter_change(interaction)

    async def on_exclude_tags_change(
        self, interaction: discord.Interaction, new_selection: Set[str]
    ):
        self.search_state.exclude_tags = new_selection
        await self.on_filter_change(interaction)

    def build_query_object(self) -> ThreadSearchQuery:
        """根据当前视图状态构建查询对象。"""
        state = self.search_state
        # 创建基础查询对象
        query = ThreadSearchQuery(
            channel_ids=state.channel_ids,
            include_authors=list(state.include_authors)
            if state.include_authors
            else None,
            exclude_authors=list(state.exclude_authors)
            if state.exclude_authors
            else None,
            include_tags=list(state.include_tags),
            exclude_tags=list(state.exclude_tags),
            keywords=state.keywords,
            exclude_keywords=state.exclude_keywords,
            exclude_keyword_exemption_markers=state.exemption_markers,
            tag_logic=state.tag_logic,
            sort_method=state.sort_method,
            sort_order=state.sort_order,
            custom_base_sort=state.custom_base_sort,
            reaction_count_range=state.reaction_count_range,
            reply_count_range=state.reply_count_range,
            created_after=state.created_after,
            created_before=state.created_before,
            active_after=state.active_after,
            active_before=state.active_before,
        )

        return self.strategy.modify_query(query)

    def build_summary_embed(self, results: dict) -> discord.Embed:
        """构建并返回一个包含当前筛选条件和结果摘要的Embed"""
        description_parts = []
        filters = []
        state = self.search_state

        if state.include_tags:
            filters.append(f"含: {', '.join(sorted(list(state.include_tags)))}")
        if state.exclude_tags:
            filters.append(f"不含: {', '.join(sorted(list(state.exclude_tags)))}")
        if state.include_authors:
            filters.append(
                f"只看作者: {', '.join([f'<@{uid}>' for uid in state.include_authors])}"
            )
        if state.exclude_authors:
            filters.append(
                f"屏蔽作者: {', '.join([f'<@{uid}>' for uid in state.exclude_authors])}"
            )
        if state.keywords:
            filters.append(f"包含关键词: {state.keywords}")
        if state.exclude_keywords:
            filters.append(f"排除关键词: {state.exclude_keywords}")

        # 时间范围
        if state.created_after:
            filters.append(f"发帖晚于: {state.created_after}")
        if state.created_before:
            filters.append(f"发帖早于: {state.created_before}")
        if state.active_after:
            filters.append(f"活跃晚于: {state.active_after}")
        if state.active_before:
            filters.append(f"活跃早于: {state.active_before}")

        # 数值范围
        if state.reaction_count_range != DefaultPreferences.DEFAULT_NUMERIC_RANGE.value:
            filters.append(f"反应数: {state.reaction_count_range}")
        if state.reply_count_range != DefaultPreferences.DEFAULT_NUMERIC_RANGE.value:
            filters.append(f"回复数: {state.reply_count_range}")

        if filters:
            description_parts.append("\n".join(filters))

        if results.get("has_results"):
            summary = f"🔍 找到 {results['total']} 个帖子 (第{results['page']}/{results['max_page']}页)"
            color = discord.Color.green()
        else:
            error_value = results.get("error")
            if error_value is True:
                summary = "搜索过程中发生错误，请稍后重试。"
            elif isinstance(error_value, str):
                summary = error_value
            else:
                summary = (
                    self.strategy.get_no_results_summary(has_filters=bool(filters))
                    or "没有找到符合条件的结果。"
                )
            color = discord.Color.orange()

        description_parts.append(summary)

        embed = discord.Embed(description="\n".join(description_parts), color=color)
        return embed

    async def refresh_view(self):
        """提供给子视图的回调，用于在数据更新后刷新此主视图"""
        if self.last_interaction:
            await self.update_view(
                self.last_interaction, rerun_search=True, from_subview=True
            )

    async def on_timeout(self):
        """当视图超时时，由于是私密消息且交互 Token 必已过期，无需（也无法）进行编辑。"""
        # 释放内存中可能存在的大型结果缓存
        self.last_search_results = None
