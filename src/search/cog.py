import discord
from discord import app_commands
from discord.ext import commands
import logging
import re
import asyncio
from typing import TYPE_CHECKING, Sequence

from shared.safe_defer import safe_defer
from .dto.tag import TagDTO
from .views.global_search_view import GlobalSearchView
from sqlalchemy.ext.asyncio import async_sessionmaker
from .search_service import SearchService
from core.tag_service import TagService
from core.cache_service import CacheService
from core.impression_cache_service import ImpressionCacheService
from search.qo.thread_search import ThreadSearchQuery
from .views.channel_selection_view import ChannelSelectionView
from config.config_service import ConfigService
from shared.enum.search_config_type import SearchConfigType, SearchConfigDefaults
from .views.generic_search_view import GenericSearchView
from .views.persistent_channel_search_view import PersistentChannelSearchView
from ..preferences.preferences_service import PreferencesService
from .views.thread_embed_builder import ThreadEmbedBuilder
from .dto.search_state import SearchStateDTO
from .strategies import AuthorSearchStrategy, CollectionSearchStrategy


if TYPE_CHECKING:
    from bot_main import MyBot

# 获取一个模块级别的 logger
logger = logging.getLogger(__name__)


class Search(commands.Cog):
    """搜索相关命令"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
        tag_service: TagService,
        cache_service: CacheService,
        preferences_service: PreferencesService,
        impression_cache_service: ImpressionCacheService,
        config_service: ConfigService,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.tag_service = tag_service
        self.cache_service = cache_service
        self.preferences_service = preferences_service
        self.impression_cache_service = impression_cache_service
        self.config_service = config_service
        self.global_search_view = GlobalSearchView(self)
        self.persistent_channel_search_view = PersistentChannelSearchView(self)
        self._has_cached_tags = False  # 用于确保 on_ready 只执行一次缓存
        logger.info("Search 模块已加载")

    async def cog_load(self):
        """在Cog加载时注册持久化View和上下文菜单"""
        # 注册持久化view
        self.bot.add_view(self.global_search_view)
        self.bot.add_view(self.persistent_channel_search_view)

        # 创建和注册上下文菜单
        search_user_context_menu = app_commands.ContextMenu(
            name="搜索作品", callback=self.search_user_posts
        )
        self.bot.tree.add_command(search_user_context_menu)

    def get_merged_tags(self, channel_ids: list[int]) -> list[TagDTO]:
        """
        获取多个频道的合并tags列表，重名tag会被合并显示
        """
        # 空列表表示搜索全部频道，直接使用预计算的全局标签缓存
        if not channel_ids:
            all_tags_names = self.cache_service.get_global_merged_tags()
        else:
            # 从指定频道获取标签并合并
            all_tags_names_set = set()
            for channel_id in channel_ids:
                channel = self.cache_service.indexed_channels.get(channel_id)
                if channel:
                    all_tags_names_set.update(
                        tag.name for tag in channel.available_tags
                    )
            all_tags_names = sorted(list(all_tags_names_set))

        # 返回 TagDTO 对象列表，确保后续代码可以安全地访问 .id 和 .name
        return [TagDTO(id=0, name=tag_name) for tag_name in all_tags_names]

    @staticmethod
    def _compile_highlight_regex(keywords_str: str) -> re.Pattern | None:
        """
        一个辅助函数，用于解析关键词字符串并返回一个编译好的正则表达式对象。
        如果关键词为空，则返回 None。
        """
        if not keywords_str:
            return None

        # 同时按逗号和斜杠分割，并去除空白
        raw_keywords = re.split(r"[，,/\s]+", keywords_str)
        cleaned_keywords = {kw.strip() for kw in raw_keywords if kw.strip()}

        if not cleaned_keywords:
            return None

        # 构建 pattern，使用 re.escape 确保特殊字符被正确处理
        pattern_str = f"({'|'.join(re.escape(kw) for kw in cleaned_keywords)})"
        return re.compile(pattern_str, re.IGNORECASE)

    @app_commands.command(
        name="创建频道搜索", description="在当前帖子内创建频道搜索按钮"
    )
    @app_commands.guild_only()
    async def create_channel_search(self, interaction: discord.Interaction):
        """在一个帖子内创建一个持久化的搜索按钮，该按钮将启动一个仅限于该频道的搜索流程。"""
        await safe_defer(interaction, ephemeral=True)
        try:
            if (
                not isinstance(interaction.channel, discord.Thread)
                or not interaction.channel.parent
            ):
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        "请在帖子内使用此命令。", ephemeral=True
                    ),
                    priority=1,
                )
                return

            channel_id = interaction.channel.parent_id

            # 创建 embed
            embed = discord.Embed(
                title=f"🔍 「{interaction.channel.parent.name} 」频道搜索",
                description=f"点击下方按钮，搜索 <#{channel_id}> 频道内的所有帖子",
                color=0x3498DB,
            )
            embed.add_field(
                name="使用方法",
                value="点击“**搜索本频道**”按钮，可以根据标签、作者、关键词等条件进行搜索。\n"
                "点击“**偏好设置**”按钮，可以修改您的默认搜索偏好。",
                inline=False,
            )

            # 发送带有持久化视图的消息
            channel = interaction.channel
            if isinstance(channel, discord.Thread):
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: channel.send(
                        embed=embed, view=self.persistent_channel_search_view
                    ),
                    priority=1,
                )
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "✅ 已成功创建频道内搜索按钮。", ephemeral=True
                ),
                priority=1,
            )
        except Exception as e:
            error_message = f"❌ 创建失败: {e}"
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    error_message, ephemeral=True
                ),
                priority=1,
            )

    @app_commands.command(
        name="创建公开全局搜索", description="在当前频道创建全局搜索面板"
    )
    async def create_global_search(self, interaction: discord.Interaction):
        """在当前频道创建一个持久化的全局搜索按钮。"""
        await safe_defer(interaction, ephemeral=True)
        try:
            embed = discord.Embed(
                title="🌐 全局搜索",
                description="搜索服务器内所有论坛频道的帖子",
                color=0x2ECC71,
            )
            embed.add_field(
                name="使用方法",
                value="1. 点击下方左侧按钮，选择要搜索的论坛频道\n"
                "2. 设置搜索条件（标签、关键词等）\n3. 查看搜索结果",
                inline=False,
            )
            embed.add_field(
                name="偏好配置",
                value="1. 点击下方右侧按钮\n"
                "2. 修改搜索时的默认配置（标签、关键词、频道等）",
                inline=False,
            )
            view = GlobalSearchView(self)
            channel = interaction.channel
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: channel.send(embed=embed, view=view),
                    priority=1,
                )
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    "✅ 已创建全局搜索面板。", ephemeral=True
                ),
                priority=1,
            )
        except Exception as e:
            error_message = f"❌ 创建失败: {e}"
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    error_message, ephemeral=True
                ),
                priority=1,
            )

    async def _create_initial_state_from_prefs(
        self, user_id: int, overrides: dict
    ) -> SearchStateDTO:
        """
        从用户偏好创建一个 SearchStateDTO，并应用指定的覆盖值。
        """
        user_prefs = await self.preferences_service.get_user_preferences(user_id)

        # 从用户偏好加载基础数据
        if user_prefs:
            prefs_data = {
                "channel_ids": user_prefs.preferred_channels or [],
                "include_authors": set(user_prefs.include_authors or []),
                "exclude_authors": set(user_prefs.exclude_authors or []),
                "include_tags": set(user_prefs.include_tags or []),
                "exclude_tags": set(user_prefs.exclude_tags or []),
                "keywords": user_prefs.include_keywords or "",
                "exclude_keywords": user_prefs.exclude_keywords or "",
                "exemption_markers": user_prefs.exclude_keyword_exemption_markers,
                "results_per_page": user_prefs.results_per_page,
                "preview_image_mode": user_prefs.preview_image_mode,
                "sort_method": user_prefs.sort_method,
                "custom_base_sort": user_prefs.custom_base_sort,
                "created_after": user_prefs.created_after,
                "created_before": user_prefs.created_before,
                "active_after": user_prefs.active_after,
                "active_before": user_prefs.active_before,
            }
        else:
            prefs_data = {}

        # 应用覆盖值 (overrides 会覆盖 prefs_data 中的同名键)
        final_data = {**prefs_data, **overrides}

        return SearchStateDTO(**final_data)

    async def _start_global_search(self, interaction: discord.Interaction):
        """
        启动全局搜索流程的通用逻辑。
        该函数会被 "/全局搜索" 命令和全局搜索按钮点击回调调用。
        """
        try:
            await safe_defer(interaction, ephemeral=True)
            # 直接从缓存中获取所有可搜索的频道
            channels = self.cache_service.get_indexed_channels()

            if not channels:
                await interaction.followup.send(
                    "❌ 未找到任何可供搜索的已索引论坛频道。\n请确保管理员已正确索引频道",
                    ephemeral=True,
                )
                return

            all_channel_ids = list(self.cache_service.indexed_channel_ids)

            initial_state = await self._create_initial_state_from_prefs(
                interaction.user.id, overrides={"all_available_tags": [], "page": 1}
            )

            view = ChannelSelectionView(
                self, interaction, channels, all_channel_ids, initial_state
            )

            embed = view.build_embed()

            await interaction.followup.send(
                content="", view=view, embed=embed, ephemeral=True
            )
        except Exception:
            logger.error("在启动全局搜索中发生严重错误", exc_info=True)
            # 确保即使有异常，也能给用户一个反馈
            if not interaction.response.is_done():
                await safe_defer(interaction, ephemeral=True)
            await interaction.followup.send(
                "❌ 启动搜索时发生严重错误，请联系技术员。", ephemeral=True
            )

    @app_commands.command(name="全局搜索", description="开始一次仅自己可见的全局搜索")
    async def start_global_search_flow(self, interaction: discord.Interaction):
        """启动全局搜索流程的通用逻辑。"""
        await self._start_global_search(interaction)

    @app_commands.command(name="搜索作者", description="快速搜索指定作者的所有帖子")
    @app_commands.describe(author="要搜索的作者（@用户 或 用户ID）")
    async def quick_author_search_command(
        self, interaction: discord.Interaction, author: discord.User
    ):
        """启动一个交互式视图，用于搜索特定作者的帖子并按标签等进行筛选。"""
        await self._quick_author_search(interaction, author)

    async def _quick_author_search(
        self, interaction: discord.Interaction, author: discord.User | discord.Member
    ):
        """快速作者搜索的内部逻辑"""
        try:
            await safe_defer(interaction, ephemeral=True)
            # 获取所有已索引的频道ID
            all_channel_ids = self.cache_service.get_indexed_channel_ids_list()
            if not all_channel_ids:
                await interaction.followup.send(
                    "❌ 未找到任何可供搜索的已索引论坛频道。", ephemeral=True
                )
                return

            # 定义需要强制覆盖用户偏好的字段
            overrides = {
                "channel_ids": all_channel_ids,
                "include_authors": {author.id},
                "exclude_authors": set(),
                "include_tags": set(),
                "exclude_tags": set(),
                "page": 1,
            }
            search_state = await self._create_initial_state_from_prefs(
                interaction.user.id, overrides
            )

            # 创建作者搜索策略
            strategy = AuthorSearchStrategy(author_id=author.id)

            # 创建通用搜索视图
            view = GenericSearchView(self, interaction, search_state, strategy=strategy)

            # 启动视图
            await view.start()

        except Exception as e:
            logger.error(f"启动搜索作者时出错: {e}", exc_info=True)
            # 确保即使有异常，也能给用户一个反馈
            if not interaction.response.is_done():
                await safe_defer(interaction, ephemeral=True)
            await interaction.followup.send(f"❌ 启动搜索作者失败: {e}", ephemeral=True)

    # 上下文菜单命令的回调函数
    async def search_user_posts(
        self, interaction: discord.Interaction, user: discord.User
    ):
        """右键点击用户，搜索该用户的作品"""
        await self._quick_author_search(interaction, author=user)

    async def search_message_author(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        """右键点击消息，搜索该消息作者的作品"""
        await self._quick_author_search(interaction, author=message.author)

    @commands.Cog.listener()
    async def on_open_collection_search(self, interaction: discord.Interaction):
        """处理收藏搜索事件"""
        await self.start_collection_search(interaction)

    async def start_collection_search(self, interaction: discord.Interaction):
        """启动用户收藏搜索流程"""
        try:
            await safe_defer(interaction, ephemeral=True)

            # 创建收藏搜索策略
            strategy = CollectionSearchStrategy(user_id=interaction.user.id)

            # 从用户偏好创建初始状态
            # 收藏搜索不预设频道和作者，但会加载用户的其他偏好
            initial_state = await self._create_initial_state_from_prefs(
                interaction.user.id, overrides={"page": 1}
            )

            # 创建 GenericSearchView 实例，并注入策略
            view = GenericSearchView(
                cog=self,
                interaction=interaction,
                search_state=initial_state,
                strategy=strategy,
            )

            # 启动视图，总是发送新的私密消息，避免修改公开面板
            await view.start(send_new_ephemeral=True)

        except Exception as e:
            logger.error(f"启动收藏搜索时出错: {e}", exc_info=True)
            if not interaction.response.is_done():
                await safe_defer(interaction, ephemeral=True)
            await interaction.followup.send("❌ 启动收藏搜索失败。", ephemeral=True)

    async def get_tags_for_author(self, author_id: int):
        """获取给定作者使用过的全部标签"""
        async with self.session_factory() as session:
            repo = SearchService(session, self.tag_service)
            return await repo.get_tags_for_author(author_id)

    async def get_indexed_channel_ids(self) -> Sequence[int]:
        """获取索引过的频道id列表"""
        return self.cache_service.get_indexed_channel_ids_list()

    async def search_and_display(
        self,
        interaction: discord.Interaction,
        search_qo: "ThreadSearchQuery",
        page: int,
        per_page: int,
        preview_mode: str,
    ) -> dict:
        """通用搜索和显示函数"""
        try:
            # 获取 UCB1 配置
            total_disp_conf = await self.config_service.get_config_from_cache(
                SearchConfigType.TOTAL_DISPLAY_COUNT
            )
            ucb_factor_conf = await self.config_service.get_config_from_cache(
                SearchConfigType.UCB1_EXPLORATION_FACTOR
            )
            strength_conf = await self.config_service.get_config_from_cache(
                SearchConfigType.STRENGTH_WEIGHT
            )

            total_display_count = (
                total_disp_conf.value_int
                if total_disp_conf and total_disp_conf.value_int is not None
                else 1
            )
            exploration_factor = (
                ucb_factor_conf.value_float
                if ucb_factor_conf and ucb_factor_conf.value_float is not None
                else SearchConfigDefaults.UCB1_EXPLORATION_FACTOR.value
            )
            strength_weight = (
                strength_conf.value_float
                if strength_conf and strength_conf.value_float is not None
                else SearchConfigDefaults.STRENGTH_WEIGHT.value
            )

            async with self.session_factory() as session:
                repo = SearchService(session, self.tag_service)
                offset = (page - 1) * per_page
                limit = per_page

                threads, total_threads = await repo.search_threads_with_count(
                    search_qo,
                    offset,
                    limit,
                    total_display_count,
                    exploration_factor,
                    strength_weight,
                )

            # 当排序方法为按创建时间排序时，不记录展示次数
            count_view = search_qo.sort_method == "created_at" or (
                search_qo.sort_method == "custom"
                and search_qo.custom_base_sort == "created_at"
            )

            # 当排序方法为按创建时间排序时，不记录展示次数
            count_view = search_qo.sort_method == "created_at" or (
                search_qo.sort_method == "custom"
                and search_qo.custom_base_sort == "created_at"
            )

            if threads and not count_view:
                thread_ids_to_update = [t.id for t in threads if t.id is not None]
                # 调用服务，将这些帖子的新增展示量存入内存缓存
                await self.impression_cache_service.increment(thread_ids_to_update)

            if not threads:
                return {"has_results": False, "total": total_threads}

            embeds = []
            if not interaction.guild:
                logger.warning("搜索时，无法获取 guild 对象，无法构建结果 embeds")
            else:
                # 预编译正则表达式
                highlight_pattern = self._compile_highlight_regex(
                    search_qo.keywords or ""
                )

                embed_tasks = [
                    ThreadEmbedBuilder.build(
                        thread,
                        interaction.guild,
                        preview_mode,
                        highlight_pattern=highlight_pattern,
                    )
                    for thread in threads
                ]
                embeds = await asyncio.gather(*embed_tasks)

            return {
                "has_results": True,
                "embeds": embeds,
                "total": total_threads,
                "page": page,
                "per_page": per_page,
                "max_page": (total_threads + per_page - 1) // per_page or 1,
            }
        except Exception:
            logger.error("在 _search_and_display 中发生错误", exc_info=True)
            return {"has_results": False, "total": 0, "error": True}
