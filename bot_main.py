import sys

if sys.platform != "win32":
    try:
        import uvloop

        uvloop.install()
        print("uvloop 已启用。")
    except ImportError:
        print("未找到 uvloop，将使用默认的 asyncio 事件循环。")


import json
import discord
import logging
from discord.ext import commands
import asyncio
from typing import cast

from shared.database import AsyncSessionFactory, init_db, close_db
from src.ThreadManager.cog import ThreadManager
from src.core.tagService import TagService
from src.core.cache_service import CacheService
from src.core.sync_service import SyncService
from src.indexer.cog import Indexer
from src.search.cog import Search
from src.preferences.cog import Preferences
from src.preferences.preferences_service import PreferencesService
from src.auditor.cog import Auditor
from src.config.cog import Configuration
from src.shared.api_scheduler import APIScheduler

logger = logging.getLogger(__name__)


class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents, config: dict):
        proxy = config.get("proxy")
        bot_kwargs = {"command_prefix": "!", "intents": intents}
        if proxy:
            bot_kwargs["proxy"] = proxy
        super().__init__(**bot_kwargs)

        self.config = config
        self.db_url = config["db_url"]
        self.tag_service: TagService
        self.cache_service: CacheService
        self.sync_service: SyncService

        # 从配置初始化API调度器
        concurrency = self.config.get("performance", {}).get(
            "api_scheduler_concurrency", 40
        )
        self.api_scheduler = APIScheduler(concurrent_requests=concurrency)

    async def process_commands(self, message: discord.Message):
        """
        重写此方法以阻止机器人处理任何文本命令。
        这可以防止因其他机器人的命令而产生 CommandNotFound 错误。
        """
        return  # 什么都不做

    async def on_index_updated_global(self):
        """接收 'index_updated' 事件并刷新缓存"""
        logger.debug("接收 'index_updated' 事件，开始刷新缓存")
        if self.tag_service:
            await self.tag_service.build_cache()
        if self.cache_service:
            await self.cache_service.build_or_refresh_cache()
        logger.info("Core 缓存刷新完毕")

    async def setup_hook(self):
        """在机器人登录前执行的初始化。"""
        # 启动API调度器
        self.api_scheduler.start()
        await init_db()

        # 1. 初始化核心服务
        self.tag_service = TagService(AsyncSessionFactory)
        self.cache_service = CacheService(self, AsyncSessionFactory)
        self.sync_service = SyncService(bot=self, session_factory=AsyncSessionFactory)
        
        asyncio.create_task(self.tag_service.build_cache())
        asyncio.create_task(self.cache_service.build_or_refresh_cache())

        # 1.5. 初始化共享服务
        preferences_service = PreferencesService(
            bot=self,
            session_factory=AsyncSessionFactory,
            tag_service=self.tag_service,
            cache_service=self.cache_service,
        )

        # 2. 加载 Cogs 并注入服务
        cogs_to_load = [
            ThreadManager(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
                cache_service=self.cache_service,
                sync_service=self.sync_service,
            ),
            Indexer(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
                tag_service=self.tag_service,
                sync_service=self.sync_service,
            ),
            Search(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
                tag_service=self.tag_service,
                cache_service=self.cache_service,
                preferences_service=preferences_service,
            ),
            Preferences(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
                preferences_service=preferences_service,
            ),
            Auditor(
                bot=self,
                session_factory=AsyncSessionFactory,
                api_scheduler=self.api_scheduler,
                sync_service=self.sync_service,
            ),
            Configuration(
                bot=self,
                session_factory=AsyncSessionFactory,
                api_scheduler=self.api_scheduler,
                tag_service=self.tag_service,
            ),
        ]
        await asyncio.gather(*(self.add_cog(cog) for cog in cogs_to_load), return_exceptions=True)
        logger.info("所有 Cogs 已加载。")

        # 3. 注册全局事件监听器
        self.add_listener(self.on_index_updated_global, "on_index_updated")

        # --- 同步应用程序命令 ---
        try:
            synced = await self.tree.sync()
            logger.info(f"成功同步 {len(synced)} 个应用程序命令。")
        except Exception as e:
            logger.error(f"同步应用程序命令时出错: {e}", exc_info=True)

    async def close(self):
        """关闭机器人时，一并关闭调度器和数据库连接。"""
        await self.api_scheduler.stop()
        await close_db()
        await super().close()


async def main():
    # 配置日志记录
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    intents.reactions = True

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    bot = MyBot(intents=intents, config=config)

    @bot.event
    async def on_ready():
        if bot.user:
            logger.info(f"机器人已登录: {bot.user} (ID: {bot.user.id})")
        else:
            logger.info("机器人已登录，但无法获取机器人信息。")

    async with bot:
        await bot.start(config["token"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("机器人关闭。")
