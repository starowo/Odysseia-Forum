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
import uvicorn

from shared.database import AsyncSessionFactory, init_db, close_db
from src.ThreadManager.cog import ThreadManager
from src.core.tag_service import TagService
from src.core.cache_service import CacheService
from src.core.sync_service import SyncService
from src.core.impression_cache_service import ImpressionCacheService
from src.core.author_service import AuthorService
from src.indexer.cog import Indexer
from src.search.cog import Search
from src.preferences.cog import Preferences
from src.preferences.preferences_service import PreferencesService
from src.auditor.cog import Auditor
from src.config.cog import Configuration
from config.config_service import ConfigService
from src.shared.api_scheduler import APIScheduler
from src.webpage.index_sync import start_index_sync
from src.api.v1.routers import (
    preferences as preferences_api,
    search as search_api,
    meta as meta_api,
)
from src.api.main import app as fastapi_app
from src.api.v1.dependencies.security import initialize_api_security

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
        self.impression_cache_service: ImpressionCacheService
        self.author_service: AuthorService

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

    def reload_config(self):
        """重新加载配置文件"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                new_config = json.load(f)

            # 更新配置
            self.config = new_config

            # 更新API调度器并发数
            concurrency = self.config.get("performance", {}).get(
                "api_scheduler_concurrency", 40
            )
            self.api_scheduler.update_concurrency(concurrency)

            logger.info("配置文件重载成功")
            return True, "配置重载成功"

        except Exception as e:
            logger.error(f"重载配置文件失败: {e}", exc_info=True)
            return False, f"配置重载失败: {e}"

    async def setup_hook(self):
        """在机器人登录前执行的初始化。"""
        # 启动API调度器
        self.api_scheduler.start()
        await init_db()

        # 确保搜索配置存在
        async with AsyncSessionFactory() as session:
            config_repo = ConfigService(session)
            await config_repo.initialize_search_configs()

        # 1. 初始化核心服务
        self.tag_service = TagService(AsyncSessionFactory)
        self.cache_service = CacheService(self, AsyncSessionFactory)
        self.author_service = AuthorService(
            bot=self, session_factory=AsyncSessionFactory
        )
        self.sync_service = SyncService(
            bot=self,
            session_factory=AsyncSessionFactory,
            author_service=self.author_service,
        )
        self.impression_cache_service = ImpressionCacheService(AsyncSessionFactory)
        self.impression_cache_service.start()

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
                impression_cache_service=self.impression_cache_service,
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
        await asyncio.gather(
            *(self.add_cog(cog) for cog in cogs_to_load), return_exceptions=True
        )
        logger.info("所有 Cogs 已加载。")

        # 3. 注册全局事件监听器
        self.add_listener(self.on_index_updated_global, "on_index_updated")

        # 4. 启动索引同步服务
        asyncio.create_task(
            start_index_sync(self, config=self.config, interval_minutes=30)
        )

        # --- 同步应用程序命令 ---
        try:
            synced = await self.tree.sync()
            logger.info(f"成功同步 {len(synced)} 个应用程序命令。")
        except Exception as e:
            logger.error(f"同步应用程序命令时出错: {e}", exc_info=True)

    async def close(self):
        """关闭机器人时，一并关闭调度器和数据库连接。"""
        await self.impression_cache_service.stop()
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

    original_setup_hook = bot.setup_hook

    # 在 setup_hook 完成后注入服务实例到 API 路由
    async def enhanced_setup_hook():
        await original_setup_hook()

        # 从已加载的 Cogs 中获取服务实例
        preferences_cog = bot.get_cog("Preferences")
        search_cog = bot.get_cog("Search")

        if preferences_cog:
            preferences_api.preferences_cog_instance = preferences_cog
        if search_cog:
            search_api.search_cog_instance = search_cog
        search_api.async_session_factory = AsyncSessionFactory
        meta_api.cache_service_instance = bot.cache_service

        logger.info("API 路由服务注入完成")

    bot.setup_hook = enhanced_setup_hook

    # 初始化 API 安全配置
    initialize_api_security()

    # 配置并并行运行 Bot 和 API 服务器
    api_config = config.get("api", {})
    uvicorn_config = uvicorn.Config(
        app=fastapi_app,
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 10810),
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    async with bot:
        await asyncio.gather(bot.start(config["token"]), server.serve())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("机器人关闭。")
