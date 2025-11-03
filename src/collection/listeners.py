import discord
from discord.ext import commands
from typing import TYPE_CHECKING
import logging

from .views.batch_collect_view import BatchCollectView
from .views.batch_uncollect_view import BatchUncollectView

from shared.models.thread import Thread
from shared.enum.collection_type import CollectionType

if TYPE_CHECKING:
    from bot_main import MyBot
    from .cog import CollectionCog

logger = logging.getLogger(__name__)


class CollectionListenerCog(commands.Cog):
    """一个专门用于处理收藏相关事件监听的Cog"""

    def __init__(self, bot: "MyBot", collection_cog: "CollectionCog"):
        self.bot = bot
        self.collection_cog = collection_cog

    @commands.Cog.listener()
    async def on_show_batch_collect_view(
        self, interaction: discord.Interaction, refresh_callback
    ):
        """监听显示批量收藏视图的事件"""

        async def fetch_data(page: int, per_page: int):
            async with self.collection_cog.get_collection_service() as service:
                return await service.get_followed_not_collected_threads(
                    interaction.user.id, page, per_page
                )

        batch_view = BatchCollectView(
            interaction=interaction,
            cog=self.collection_cog,
            title="批量收藏（已关注但未收藏）",
            fetch_data_func=fetch_data,
            refresh_callback=refresh_callback,
        )
        await batch_view.start()

    @commands.Cog.listener()
    async def on_show_batch_uncollect_view(
        self, interaction: discord.Interaction, refresh_callback
    ):
        """监听显示批量取消收藏视图的事件"""

        async def fetch_data(page: int, per_page: int):
            async with self.collection_cog.get_collection_service() as service:
                return await service.get_collected_targets(
                    interaction.user.id,
                    CollectionType.THREAD,
                    page,
                    per_page,
                    Thread,
                )

        batch_view = BatchUncollectView(
            interaction=interaction,
            cog=self.collection_cog,
            title="批量取消收藏",
            fetch_data_func=fetch_data,
            refresh_callback=refresh_callback,
        )
        await batch_view.start()
