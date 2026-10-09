import asyncio
import logging
import re
from typing import TYPE_CHECKING, Sequence

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.preferences_repository import PreferencesRepository
from core.tag_repository import TagRepository
from dto import ThreadDTO
from search.dto.search_state import SearchStateDTO
from search.dto.separated_tags import SeparatedTagsDTO
from search.qo.thread_search import ThreadSearchQuery
from search.search_service import SearchService
from shared.channel_mapping_utils import ChannelMappingUtils
from shared.permissions import is_admin_or_bot_admin
from search.strategies import AuthorSearchStrategy, CollectionSearchStrategy
from search.views import (
    ChannelSelectionView,
    GenericSearchView,
    GlobalSearchView,
    PersistentChannelSearchView,
    ThreadEmbedBuilder,
)
from shared.enum import SearchConfigDefaultsInt, SearchConfigType
from shared.safe_defer import safe_defer
from shared.abyss_tag_visibility import can_discord_user_view_abyss_tags

if TYPE_CHECKING:
    from bot_main import MyBot

logger = logging.getLogger(__name__)


class Search(commands.Cog):
    """搜索相关命令"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        config: dict,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.config = config
        self.tag_service = bot.tag_cache_service
        self.cache_service = bot.cache_service
        self.impression_cache_service = bot.impression_cache_service
        self.global_search_view = GlobalSearchView(self)
        self.persistent_channel_search_view = PersistentChannelSearchView(self)
        self._has_cached_tags = False  # 用于确保 on_ready 只执行一次缓存

        # 初始化频道映射工具
        self.channel_mappings_config = self._build_channel_mappings_config()
        self.channel_mappings_utils = ChannelMappingUtils(self.channel_mappings_config)

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

    def _build_channel_mappings_config(self) -> dict[int, list[dict]]:
        """解析构建内部供映射服务使用的配置字典"""
        raw_mappings = self.config.get("channel_mappings", {})
        parsed_mappings = {}
        for key, val in raw_mappings.items():
            if key.startswith("_") or not isinstance(val, list):
                continue
            try:
                ch_id = int(key)
            except (ValueError, TypeError):
                continue
            parsed_mappings[ch_id] = [
                {
                    "tag_name": mapping["tag_name"],
                    "source_channel_ids": [
                        int(cid) for cid in mapping.get("source_channel_ids", [])
                    ],
                }
                for mapping in val
                if isinstance(mapping, dict) and "tag_name" in mapping
            ]
        return parsed_mappings

    def _get_main_guild_id_from_config(self) -> int:
        """从配置文件读取主服务器 ID；为空时回退到默认值。"""
        raw_main_guild_id = self.config.get("main_guild_id")
        if raw_main_guild_id in (None, ""):
            return int(SearchConfigDefaultsInt.MAIN_GUILD_ID.value)

        try:
            return int(raw_main_guild_id)
        except (TypeError, ValueError):
            logger.warning(
                "config.json 中的 main_guild_id 无法解析，已回退到默认主服务器 ID。"
            )
            return int(SearchConfigDefaultsInt.MAIN_GUILD_ID.value)

    def can_view_abyss_tags(self, user_id: int) -> bool:
        """按主服务器身份组判断 BOT 候选中的深渊向 TAG 可见性。"""
        return can_discord_user_view_abyss_tags(
            self.bot,
            user_id,
            self._get_main_guild_id_from_config(),
            self.config.get("abyss", {}),
        )

    async def get_merged_tags_separated(
        self, channel_ids: list[int], *, include_abyss: bool
    ) -> SeparatedTagsDTO:
        """获取分离的虚拟标签和所有可用标签，确保虚拟标签排在最前"""
        real_tags_set = set()
        virtual_tags_set = set()

        if not channel_ids:
            # 全局搜索：获取所有频道的虚拟标签和真实标签
            for mappings in self.channel_mappings_utils.channel_mappings.values():
                for mapping in mappings:
                    virtual_tags_set.add(mapping["tag_name"])
            async with self.session_factory() as session:
                tags = await TagRepository(
                    session
                ).get_all_unique_tags_from_indexed_threads(
                    source="discord", include_abyss=include_abyss
                )
            real_tags_set = {tag.name for tag in tags}
        else:
            # 特定频道搜索：获取指定频道的虚拟标签和真实标签
            for channel_id in channel_ids:
                channel = self.cache_service.indexed_channels.get(channel_id)
                if channel:
                    real_tags_set.update(tag.name for tag in channel.available_tags)

                mappings = self.channel_mappings_utils.channel_mappings.get(
                    channel_id, []
                )
                for mapping in mappings:
                    virtual_tags_set.add(mapping["tag_name"])

            async with self.session_factory() as session:
                real_tags_set = await TagRepository(session).filter_candidate_names(
                    real_tags_set, include_abyss=include_abyss
                )

        # 分别排序，然后确保虚拟标签在前
        sorted_virtual = sorted(list(virtual_tags_set))

        # 真实标签中排除虚拟标签，避免重复展示
        sorted_real = sorted(list(real_tags_set - virtual_tags_set))

        all_tags = sorted_virtual + sorted_real
        return SeparatedTagsDTO(virtual_tags=sorted_virtual, all_tags=all_tags)

    @staticmethod
    def _compile_highlight_regex(keywords_str: str) -> re.Pattern | None:
        """
        一个辅助函数，用于解析关键词字符串并返回一个编译好的正则表达式对象。
        如果关键词为空，则返回 None。
        """
        if not keywords_str:
            return None

        # 同时按逗号和斜杠分割，并去除空白
        raw_keywords = re.split(r"[，,/\\\s]+", keywords_str)
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
    @is_admin_or_bot_admin()
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
    @is_admin_or_bot_admin()
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
        self, user_id: int, overrides: dict, guild_id: int = 0
    ) -> SearchStateDTO:
        """
        从用户偏好创建一个 SearchStateDTO，并应用指定的覆盖值。
        """
        # 如果没传有效 guild_id，使用 config 里的 main_guild_id
        if not guild_id or guild_id == 0:
            guild_id = self._get_main_guild_id_from_config()

        async with self.session_factory() as session:
            repo = PreferencesRepository(session)
            user_prefs = await repo.get_user_preferences(user_id, guild_id)

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
        """启动全局搜索流程的通用逻辑，强制应用主服务器配置"""
        try:
            await safe_defer(interaction, ephemeral=True)

            # 使用主服务器 ID 获取频道
            main_guild_config = await self.cache_service.get_bot_config(
                SearchConfigType.MAIN_GUILD_ID
            )
            target_guild_id = (
                main_guild_config.value_int
                if main_guild_config and main_guild_config.value_int
                else interaction.guild_id
            )

            channels = self.cache_service.get_indexed_channels(target_guild_id)

            if not channels:
                await interaction.followup.send(
                    "❌ 未找到任何可供搜索的已索引论坛频道。\n"
                    "请确保管理员已正确索引频道",
                    ephemeral=True,
                )
                return

            all_channel_ids = self.cache_service.get_indexed_channel_ids_list(
                target_guild_id
            )

            initial_state = await self._create_initial_state_from_prefs(
                interaction.user.id,
                overrides={"all_available_tags": [], "page": 1},
                guild_id=target_guild_id or 0,
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

            main_guild_config = await self.cache_service.get_bot_config(
                SearchConfigType.MAIN_GUILD_ID
            )
            target_guild_id = (
                main_guild_config.value_int
                if main_guild_config and main_guild_config.value_int
                else interaction.guild_id
            )

            all_channel_ids = self.cache_service.get_indexed_channel_ids_list(
                target_guild_id
            )
            if not all_channel_ids:
                await interaction.followup.send(
                    "❌ 未找到任何可供搜索的已索引论坛频道。", ephemeral=True
                )
                return

            overrides = {
                "channel_ids": all_channel_ids,
                "include_authors": {author.id},
                "exclude_authors": set(),
                "include_tags": set(),
                "exclude_tags": set(),
                "page": 1,
            }
            search_state = await self._create_initial_state_from_prefs(
                interaction.user.id,
                overrides,
                guild_id=target_guild_id or 0,
            )

            strategy = AuthorSearchStrategy(author_id=author.id)
            view = GenericSearchView(self, interaction, search_state, strategy=strategy)
            await view.start()

        except Exception as e:
            logger.error(f"启动搜索作者时出错: {e}", exc_info=True)
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

    @app_commands.command(name="查看收藏", description="查看和搜索您已收藏的帖子")
    async def view_collections_command(self, interaction: discord.Interaction):
        """查看收藏"""
        await self.start_collection_search(interaction)

    @commands.Cog.listener()
    async def on_open_collection_search(self, interaction: discord.Interaction):
        """处理收藏搜索事件"""
        await self.start_collection_search(interaction)

    async def start_collection_search(self, interaction: discord.Interaction):
        """启动用户收藏搜索流程"""
        try:
            await safe_defer(interaction, ephemeral=True)

            main_guild_config = await self.cache_service.get_bot_config(
                SearchConfigType.MAIN_GUILD_ID
            )
            target_guild_id = (
                main_guild_config.value_int
                if main_guild_config and main_guild_config.value_int
                else interaction.guild_id
            )

            strategy = CollectionSearchStrategy(user_id=interaction.user.id)
            initial_state = await self._create_initial_state_from_prefs(
                interaction.user.id,
                overrides={"page": 1},
                guild_id=target_guild_id or 0,
            )

            view = GenericSearchView(
                cog=self,
                interaction=interaction,
                search_state=initial_state,
                strategy=strategy,
            )
            await view.start(send_new_ephemeral=True)

        except Exception as e:
            logger.error(f"启动收藏搜索时出错: {e}", exc_info=True)
            if not interaction.response.is_done():
                await safe_defer(interaction, ephemeral=True)
            await interaction.followup.send("❌ 启动收藏搜索失败。", ephemeral=True)

    async def get_tags_for_author(
        self, author_id: int, *, include_abyss: bool = True
    ):
        """获取给定作者使用过的全部标签"""
        async with self.session_factory() as session:
            repo = SearchService(session, self.tag_service)
            return await repo.get_tags_for_author(
                author_id, include_abyss=include_abyss
            )

    async def get_custom_tag_names(self, names: set[str]) -> set[str]:
        """识别搜索状态中需静默保留的自定义 TAG 名称。"""
        async with self.session_factory() as session:
            return await TagRepository(session).custom_names(names)

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
        """解析虚拟标签、执行数据库搜索并构建结果 Embed 列表"""
        try:
            # 提取所有已被索引的频道ID，用于计算
            all_indexed_channels = self.cache_service.get_indexed_channel_ids_list()

            # 运用频道映射工具类解析并提取真实数据库需检索的标签和频道
            resolution = self.channel_mappings_utils.resolve(
                channel_ids=search_qo.channel_ids,
                include_tags=search_qo.include_tags,
                exclude_tags=search_qo.exclude_tags,
                tag_logic=search_qo.tag_logic,
                all_indexed_channels=all_indexed_channels,
            )
            original_channel_ids = search_qo.channel_ids

            search_qo.channel_ids = resolution.effective_channel_ids
            search_qo.include_tags = resolution.effective_include_tags
            search_qo.exclude_tags = resolution.effective_exclude_tags

            # 为了支持子服检索，将限制的 guild_id 置空
            search_qo.guild_id = None

            # 获取 UCB1 配置
            ucb1_config = await self.cache_service.get_ucb1_config()

            async with self.session_factory() as session:
                repo = SearchService(session, self.tag_service)
                offset = (page - 1) * per_page
                threads, total_threads = await repo.search_threads_with_count(
                    search_qo,
                    limit=per_page,
                    offset=offset,
                    total_display_count=ucb1_config.total_display_count,
                    exploration_factor=ucb1_config.exploration_factor,
                    strength_weight=ucb1_config.strength_weight,
                    time_decay=ucb1_config.reddit_hot_time_decay,
                )
                # 在 session 内将 ORM 对象转为 DTO，确保 session 关闭后可安全访问
                thread_dtos = [ThreadDTO.from_orm(t) for t in threads]

            # 当排序方法为按创建时间或收藏时间排序时，不记录展示次数
            count_view = not (
                search_qo.sort_method in ["created_at", "collected_at"]
                or (
                    search_qo.sort_method == "custom"
                    and search_qo.custom_base_sort in ["created_at", "collected_at"]
                )
            )

            if thread_dtos and count_view:
                thread_ids_to_update = [t.id for t in thread_dtos if t.id is not None]
                await self.impression_cache_service.increment(thread_ids_to_update)

            if not thread_dtos:
                return {"has_results": False, "total": total_threads}

            # 为帖子详情 embed 提取用于渲染的虚拟标签关联
            origins = (
                original_channel_ids
                if original_channel_ids
                else list(self.channel_mappings_utils.channel_mappings.keys())
            )
            channel_to_virtual = (
                self.channel_mappings_utils.get_channel_virtual_tags_map(origins)
            )

            embeds = []
            if not interaction.guild:
                logger.warning(
                    "搜索时，无法获取 guild 对象，可能导致 fallback URL 异常"
                )

            highlight_pattern = self._compile_highlight_regex(search_qo.keywords or "")
            embed_tasks = []
            for thread_dto in thread_dtos:
                matched_virtual_tags = channel_to_virtual.get(thread_dto.channel_id, [])
                task = ThreadEmbedBuilder.build(
                    thread=thread_dto,
                    guild=interaction.guild,
                    preview_mode=preview_mode,
                    highlight_pattern=highlight_pattern,
                    virtual_tags=matched_virtual_tags,
                )
                embed_tasks.append(task)

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

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """
        Cog 级别的应用程序命令错误处理器。
        """
        if isinstance(error, app_commands.CheckFailure):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ 你没有权限使用此命令。需要服务器管理员或被指定为机器人管理员。",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ 你没有权限使用此命令。需要服务器管理员或被指定为机器人管理员。",
                    ephemeral=True,
                )
        else:
            command_name = interaction.command.name if interaction.command else "未知"
            logger.error(f"命令 '{command_name}' 发生错误", exc_info=error)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ 命令执行时发生未知错误: {error}", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ 命令执行时发生未知错误: {error}", ephemeral=True
                )
