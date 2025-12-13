import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from collection.listeners import CollectionListenerCog
from core.collection_service import CollectionService
from core.thread_service import ThreadService
from shared.enum.collection_type import CollectionType
from shared.safe_defer import safe_defer

if TYPE_CHECKING:
    from bot_main import MyBot
    from collection.listeners import CollectionListenerCog

logger = logging.getLogger(__name__)


class CollectionCog(commands.Cog, name="CollectionCog"):
    """处理帖子收藏相关功能"""

    def __init__(self, bot: "MyBot", session_factory: async_sessionmaker):
        self.bot = bot
        self.session_factory = session_factory

    @asynccontextmanager
    async def get_collection_service(self) -> AsyncIterator[CollectionService]:
        """提供一个 CollectionService 的实例，并管理 session 的生命周期"""
        async with self.session_factory() as session:
            yield CollectionService(session)

    @asynccontextmanager
    async def get_thread_service(self) -> AsyncIterator[ThreadService]:
        """提供一个 ThreadService 的实例，并管理 session 的生命周期"""
        async with self.session_factory() as session:
            yield ThreadService(session)

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """提供一个数据库 session，用于需要多个服务协同工作的场景"""
        async with self.session_factory() as session:
            yield session

    async def cog_load(self):
        """在Cog加载时，注册上下文菜单并加载监听器 Cog"""

        # 加载监听器 Cog
        await self.bot.add_cog(CollectionListenerCog(self.bot, self))

        # 注册上下文菜单
        collect_menu = app_commands.ContextMenu(
            name="⭐ 收藏此帖",
            callback=self.collect_thread_context_menu,
        )
        remove_menu = app_commands.ContextMenu(
            name="➖ 移除收藏",
            callback=self.remove_collection_context_menu,
        )
        self.bot.tree.add_command(collect_menu)
        self.bot.tree.add_command(remove_menu)
        logger.info("Collection 模块已加载")

    async def collect_thread_context_menu(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        """右键菜单命令：收藏此帖"""
        await safe_defer(interaction, ephemeral=True)

        if not isinstance(message.channel, discord.Thread):
            await interaction.followup.send(
                "❌ 此命令只能对帖子内的消息使用。", ephemeral=True
            )
            return

        thread_id = message.channel.id
        user_id = interaction.user.id

        async with self.get_session() as session:
            collection_service = CollectionService(session)
            success = await collection_service.add_collection(
                user_id=user_id, target_type=CollectionType.THREAD, target_id=thread_id
            )
            if success:
                thread_service = ThreadService(session)
                await thread_service.update_collection_counts([thread_id], 1)

        if success:
            await interaction.followup.send(
                f"✅ 「 **{message.channel.name}** 」已成功添加至您的收藏！", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"🤔 您之前已经收藏过「 **{message.channel.name}** 」了", ephemeral=True
            )

    async def remove_collection_context_menu(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        """右键菜单命令：移除收藏"""
        await safe_defer(interaction, ephemeral=True)

        if not isinstance(message.channel, discord.Thread):
            await interaction.followup.send(
                "❌ 此命令只能对帖子内的消息使用。", ephemeral=True
            )
            return

        thread_id = message.channel.id
        user_id = interaction.user.id

        async with self.get_session() as session:
            collection_service = CollectionService(session)
            success = await collection_service.remove_collection(
                user_id=user_id, target_type=CollectionType.THREAD, target_id=thread_id
            )
            if success:
                thread_service = ThreadService(session)
                await thread_service.update_collection_counts([thread_id], -1)

        if success:
            await interaction.followup.send(
                f"🗑️ **{message.channel.name}** 已从您的收藏中移除。", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"🤔 您尚未收藏过 **{message.channel.name}**。", ephemeral=True
            )
