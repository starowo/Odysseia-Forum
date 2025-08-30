from __future__ import annotations
import logging
from venv import logger
import discord
from discord import app_commands
from datetime import datetime, timezone
import re
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import async_sessionmaker
from core.cache_service import CacheService
from shared.safe_defer import safe_defer
from shared.utils import process_string_to_set # 导入新工具函数
from .repository import PreferencesRepository
from src.search.dto.user_search_preferences import UserSearchPreferencesDTO
from core.tagService import TagService
from ..search.views.components.keyword_button import KeywordModal
from .views.tag_preferences_view import TagPreferencesView
from .views.channel_preferences_view import ChannelPreferencesView
from preferences.repository import PreferencesRepository

if TYPE_CHECKING:
    from .views.preferences_view import PreferencesView
    from ..search.cog import Search

# 获取一个模块级别的 logger
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from bot_main import MyBot

class PreferencesService:
    """处理用户搜索偏好设置"""

    def __init__(
        self,
        bot: "MyBot",
        session_factory: async_sessionmaker,
        tag_service: TagService,
        cache_service: CacheService,
    ):
        self.bot = bot
        self.session_factory = session_factory
        self.tag_service = tag_service
        self.cache_service = cache_service

    async def get_user_preferences(
        self, user_id: int
    ) -> Optional[UserSearchPreferencesDTO]:
        """获取并返回用户的搜索偏好 DTO"""
        async with self.session_factory() as session:
            repo = PreferencesRepository(session, self.tag_service)
            return await repo.get_user_preferences(user_id)

    async def save_user_preferences(
        self, user_id: int, prefs_data: dict
    ) -> UserSearchPreferencesDTO:
        """创建或更新用户的搜索偏好设置"""
        async with self.session_factory() as session:
            repo = PreferencesRepository(session, self.tag_service)
            return await repo.save_user_preferences(user_id, prefs_data)

    async def save_user_keywords(
        self,
        user_id: int,
        include_str: str,
        exclude_str: str,
        exemption_markers_str: str,
    ) -> UserSearchPreferencesDTO:
        """接收关键词字符串，处理并保存到数据库。"""
        
        final_include_set = process_string_to_set(include_str)
        final_exclude_set = process_string_to_set(exclude_str)
        final_exemption_markers_list = sorted(
            list(process_string_to_set(exemption_markers_str))
        )

        final_include_str = ", ".join(sorted(list(final_include_set)))
        final_exclude_str = ", ".join(sorted(list(final_exclude_set)))

        async with self.session_factory() as session:
            repo = PreferencesRepository(session, self.tag_service)
            return await repo.save_user_preferences(
                user_id,
                {
                    "include_keywords": final_include_str,
                    "exclude_keywords": final_exclude_str,
                    "exclude_keyword_exemption_markers": final_exemption_markers_list,
                },
            )

    async def search_preferences_author(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        user: Optional[discord.User] = None,
    ):
        await safe_defer(interaction, ephemeral=True)
        try:
            user_id = interaction.user.id
            if action.value in ["include", "exclude", "unblock"] and not user:
                await self.bot.api_scheduler.submit(
                    coro_factory=lambda: interaction.followup.send(
                        "❌ 请指定要设置的用户。", ephemeral=True
                    ),
                    priority=1,
                )
                return

            async with self.session_factory() as session:
                repo = PreferencesRepository(session, self.tag_service)
                prefs = await repo.get_user_preferences(user_id)

                if not prefs:
                    prefs_data = {"include_authors": [], "exclude_authors": []}
                else:
                    prefs_data = {
                        "include_authors": prefs.include_authors or [],
                        "exclude_authors": prefs.exclude_authors or [],
                    }

                include_authors = set(prefs_data["include_authors"])
                exclude_authors = set(prefs_data["exclude_authors"])

                if action.value == "clear":
                    include_authors.clear()
                    exclude_authors.clear()
                    message = "✅ 已清空所有作者偏好设置。"
                elif user:
                    if action.value == "include":
                        include_authors.add(user.id)
                        exclude_authors.discard(user.id)
                        message = f"✅ 已将 {user.mention} 添加到只看作者列表。"
                    elif action.value == "exclude":
                        exclude_authors.add(user.id)
                        include_authors.discard(user.id)
                        message = f"✅ 已将 {user.mention} 添加到屏蔽作者列表。"
                    elif action.value == "unblock":
                        if user.id in exclude_authors:
                            exclude_authors.remove(user.id)
                            message = f"✅ 已将 {user.mention} 从屏蔽列表中移除。"
                        else:
                            message = f"ℹ️ {user.mention} 不在屏蔽列表中。"

                await repo.save_user_preferences(
                    user_id,
                    {
                        "include_authors": list(include_authors),
                        "exclude_authors": list(exclude_authors),
                    },
                )

            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(message, ephemeral=True),
                priority=1,
            )
        except Exception as e:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    f"❌ 操作失败: {e}", ephemeral=True
                ),
                priority=1,
            )

    async def search_preferences_channels(
        self, interaction: discord.Interaction, parent_view: "PreferencesView"
    ):
        """处理 /搜索偏好 频道 命令，启动频道偏好设置视图。"""
        await safe_defer(interaction, ephemeral=True)
        try:
            async with self.session_factory() as session:
                repo = PreferencesRepository(session, self.tag_service)
                prefs_dto = await repo.get_user_preferences(interaction.user.id)
                if not prefs_dto:
                    prefs_dto = UserSearchPreferencesDTO(user_id=interaction.user.id)
            
            indexed_channels = self.cache_service.get_indexed_channels()

            view = ChannelPreferencesView(
                self, interaction, parent_view, prefs_dto, indexed_channels
            )
            await view.start()

        except Exception as e:
            logger.error(f"打开频道偏好设置时出错: {e}", exc_info=True)
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    f"❌ 打开频道设置时出错: {e}", ephemeral=True
                ),
                priority=1,
            )

    async def save_preferred_channels(self, user_id: int, channel_ids: List[int]):
        """保存用户的默认搜索频道列表"""
        async with self.session_factory() as session:
            repo = PreferencesRepository(session, self.tag_service)
            await repo.save_user_preferences(
                user_id,
                {"preferred_channels": channel_ids},
            )
            # logger.info(f"用户 {user_id} 的默认搜索频道已保存: {channel_ids}")

    async def update_user_time_range(
        self,
        user_id: int,
        after_date_str: Optional[str],
        before_date_str: Optional[str],
    ) -> None:
        """
        更新用户的时间范围偏好设置。
        此方法只处理业务逻辑，不发送任何 discord 响应。

        :param user_id: 用户 ID。
        :param after_date_str: 开始日期字符串 (YYYY-MM-DD)。
        :param before_date_str: 结束日期字符串 (YYYY-MM-DD)。
        :raises ValueError: 如果日期格式无效。
        """
        update_data = {}
        if after_date_str:
            naive_dt = datetime.strptime(after_date_str, "%Y-%m-%d")
            update_data["after_date"] = naive_dt.replace(tzinfo=timezone.utc)
        if before_date_str:
            naive_dt = datetime.strptime(before_date_str, "%Y-%m-%d")
            aware_dt = naive_dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            update_data["before_date"] = aware_dt

        if not after_date_str and not before_date_str:
            update_data = {"after_date": None, "before_date": None}

        async with self.session_factory() as session:
            repo = PreferencesRepository(session, self.tag_service)
            await repo.save_user_preferences(user_id, update_data)

    async def search_preferences_tags(
        self, interaction: discord.Interaction, parent_view: "PreferencesView"
    ):
        """处理 /搜索偏好 标签 命令，启动标签偏好设置视图。"""
        await safe_defer(interaction, ephemeral=True)
        try:
            async with self.session_factory() as session:
                repo = PreferencesRepository(session, self.tag_service)

                # 1. 获取所有可用标签
                all_tags = self.tag_service.get_unique_tag_names()

                # 2. 获取用户当前偏好
                prefs_dto = await repo.get_user_preferences(interaction.user.id)
                if not prefs_dto:
                    # 创建一个新的DTO，但暂时不保存到数据库
                    # 直到用户点击保存时，才会通过 save_tag_preferences 创建记录
                    prefs_dto = UserSearchPreferencesDTO(user_id=interaction.user.id)

            # 3. 启动视图
            view = TagPreferencesView(
                self, interaction, parent_view, prefs_dto, all_tags
            )
            await view.start()

        except Exception as e:
            await self.bot.api_scheduler.submit(
                coro_factory=lambda: interaction.followup.send(
                    f"❌ 打开标签设置时出错: {e}", ephemeral=True
                ),
                priority=1,
            )

    async def save_tag_preferences(
        self,
        interaction: discord.Interaction,
        include_tags: List[str],
        exclude_tags: List[str],
    ):
        """由 TagPreferencesView 回调，用于保存标签偏好。"""
        try:
            async with self.session_factory() as session:
                repo = PreferencesRepository(session, self.tag_service)
                await repo.save_user_preferences(
                    interaction.user.id,
                    {
                        "include_tags": include_tags,
                        "exclude_tags": exclude_tags,
                    },
                )
        except Exception as e:
            # 在视图中已经处理了对用户的响应，这里只记录日志
            logger.error(f"保存 Tag 偏好时出错: {e}")

    async def toggle_preview_mode(self, user_id: int) -> None:
        """切换用户的预览图显示模式（大图/缩略图）。"""
        async with self.session_factory() as session:
            repo = PreferencesRepository(session, self.tag_service)
            prefs = await repo.get_user_preferences(user_id)

            current_mode = "thumbnail"  # 默认值
            if prefs and prefs.preview_image_mode:
                current_mode = prefs.preview_image_mode

            new_mode = "image" if current_mode == "thumbnail" else "thumbnail"

            await repo.save_user_preferences(user_id, {"preview_image_mode": new_mode})

    async def clear_user_preferences(self, user_id: int) -> None:
        """清空指定用户的所有搜索偏好设置"""
        async with self.session_factory() as session:
            repo = PreferencesRepository(session, self.tag_service)
            await repo.save_user_preferences(
                user_id,
                {
                    "include_authors": [],
                    "exclude_authors": [],
                    "after_date": None,
                    "before_date": None,
                    "preview_image_mode": "thumbnail",
                    "results_per_page": 5,
                    "include_tags": [],
                    "exclude_tags": [],
                    "include_keywords": "",
                    "exclude_keywords": "",
                    "preferred_channels": [],
                },
            )
