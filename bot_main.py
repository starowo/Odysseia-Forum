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
from logging.handlers import TimedRotatingFileHandler
from discord.ext import commands
import asyncio
import time
import os

from dotenv import load_dotenv
from shared.database import AsyncSessionFactory, init_db, close_db
from shared.redis_client import RedisManager
from ThreadManager.cog import ThreadManager
from core.tag_cache_service import TagCacheService
from core.cache_service import CacheService
from core.redis_trend_service import RedisTrendService
from core.sync_service import SyncService
from open_graph.reindex_consumer import OpenGraphReindexConsumer
from open_graph.reindex_queue import OpenGraphReindexQueue
from core.impression_cache_service import ImpressionCacheService
from core.discord_parser_patch import install_uncached_thread_members_patch
from indexer.cog import Indexer
from search.cog import Search
from preferences.cog import Preferences
from auditor.cog import Auditor
from config.cog import Configuration
from banner.cog import BannerManagement
from banner.listeners.banner_event_listener import BannerEventListener
from core.config_repository import ConfigRepository
from collection.cog import CollectionCog
from update_detector.cog import UpdateDetector
from author.cog import AuthorCog
from backup.cog import BackupCog
from shared.api_scheduler import APIScheduler
from shared.enum import SearchConfigDefaultsInt
from shared.event_mediator import EventMediator
from tag.cog import TagCog
from dto.events import IndexUpdatedEvent

load_dotenv()

logger = logging.getLogger(__name__)


class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents, config: dict):
        proxy = config.get("proxy")
        bot_kwargs = {
            "command_prefix": "!",
            "intents": intents,
            "max_messages": 0,
            "chunk_guilds_at_startup": False,
        }
        if proxy:
            bot_kwargs["proxy"] = proxy
        super().__init__(**bot_kwargs)
        install_uncached_thread_members_patch(self)

        self.config = config
        self.tag_cache_service: TagCacheService
        self.cache_service: CacheService
        self.sync_service: SyncService
        self.open_graph_reindex_consumer: OpenGraphReindexConsumer
        self.impression_cache_service: ImpressionCacheService
        self.event_mediator = EventMediator()

        # 从配置初始化API调度器
        concurrency = self.config.get("performance", {}).get(
            "api_scheduler_concurrency", 40
        )
        self.api_scheduler = APIScheduler(concurrent_requests=concurrency)

        # 健康监控状态（Plan A + C）
        self._connected: bool = False
        # 从 Bot 创建时开始计时，防止首次连接失败时 _disconnected_at 为 None
        # 导致看门狗和健康检查双双失效（启动死锁）。
        self._disconnected_at: float | None = time.monotonic()
        # Docker 工作目录为 /app，本地 Windows 为项目根目录
        self._heartbeat_path: str = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "bot_heartbeat.json"
        )
        os.makedirs(os.path.dirname(self._heartbeat_path), exist_ok=True)
        self._max_disconnect_seconds: float = 300.0  # 5 分钟断连后自愈退出
        self._health_exit_code: int = 0
        self._closing: bool = False  # close() 重入守卫

    async def process_commands(self, message: discord.Message):
        """
        重写此方法以阻止机器人处理任何文本命令。
        这可以防止因其他机器人的命令而产生 CommandNotFound 错误。
        """
        return  # 什么都不做

    async def on_index_updated_global(self, event: IndexUpdatedEvent):
        """接收 'index_updated' 事件并刷新缓存"""
        logger.debug("接收 'index_updated' 事件，开始刷新缓存")
        tasks = []
        if self.tag_cache_service:
            tasks.append(self.tag_cache_service.build_cache())
        if self.cache_service:
            tasks.append(self.cache_service.build_or_refresh_cache())

        if tasks:
            await asyncio.gather(*tasks)

        # 刷新后重新发布频道元数据到 Redis
        if self.cache_service:
            await self.cache_service.publish_channel_metadata(RedisManager.get_client())
        logger.info("核心缓存刷新完毕")

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

        main_guild_id = self._get_main_guild_id_from_config()

        # 确保搜索配置存在
        async with AsyncSessionFactory() as session:
            config_repository = ConfigRepository(session)
            await config_repository.initialize_search_configs(main_guild_id)

        # 初始化核心服务
        self.tag_cache_service = TagCacheService(AsyncSessionFactory)
        self.cache_service = CacheService(self, AsyncSessionFactory)
        self.sync_service = SyncService(
            bot=self,
            session_factory=AsyncSessionFactory,
        )
        self.open_graph_reindex_consumer = OpenGraphReindexConsumer(
            sync_service=self.sync_service,
            reindex_queue=OpenGraphReindexQueue(RedisManager.get_client()),
        )
        self.open_graph_reindex_consumer.start()
        self.impression_cache_service = ImpressionCacheService(
            session_factory=AsyncSessionFactory, bot=self
        )
        self.impression_cache_service.start()

        # 并行构建缓存
        await asyncio.gather(
            self.tag_cache_service.build_cache(),
            self.cache_service.build_or_refresh_cache(),
        )

        # 将频道元数据发布到 Redis，供 API 进程读取
        await self.cache_service.publish_channel_metadata(RedisManager.get_client())

        # 加载 Cogs
        cogs_to_load = [
            ThreadManager(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
            ),
            Indexer(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
            ),
            Search(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
            ),
            Preferences(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
            ),
            Auditor(
                bot=self,
                session_factory=AsyncSessionFactory,
            ),
            Configuration(
                bot=self,
                session_factory=AsyncSessionFactory,
            ),
            BannerManagement(
                bot=self,
                session_factory=AsyncSessionFactory,
            ),
            BannerEventListener(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config.get("banner", {}),
            ),
            CollectionCog(
                bot=self,
                session_factory=AsyncSessionFactory,
            ),
            UpdateDetector(
                bot=self,
                session_factory=AsyncSessionFactory,
                config=self.config,
            ),
            AuthorCog(
                bot=self,
                session_factory=AsyncSessionFactory,
            ),
            BackupCog(bot=self, config=self.config),
            TagCog(self, AsyncSessionFactory, self.config),
        ]
        await asyncio.gather(
            *(self.add_cog(cog) for cog in cogs_to_load), return_exceptions=True
        )
        logger.info("所有 Cogs 已加载。")

        # 由组合根注册跨业务模块的可等待事件处理器。
        self.event_mediator.register(
            IndexUpdatedEvent,
            self.on_index_updated_global,
        )

        # 启动健康监控后台任务
        asyncio.create_task(self._heartbeat_writer())
        asyncio.create_task(self._disconnect_timeout_monitor())

        # --- 同步应用程序命令 ---
        try:
            synced = await self.tree.sync()
            logger.info(f"成功同步 {len(synced)} 个应用程序命令。")
        except Exception as e:
            logger.error(f"同步应用程序命令时出错: {e}", exc_info=True)

    # -------------------------
    # 健康监控
    # -------------------------

    async def on_connect(self):
        """当 bot 建立（或重新建立）Discord 网关连接时调用。"""
        self._connected = True
        self._disconnected_at = None
        logger.info("已连接到 Discord 网关")

    async def on_disconnect(self):
        """当 bot 与 Discord 网关断开连接时调用。

        「_connected」守卫：discord.py 的重连循环在每次失败时
        都会 dispatch 'disconnect'，不加守卫会导致断连时间戳被反复重置，
        使得 _disconnect_timeout_monitor 永远达不到超时阈值。
        """
        if self._connected:
            self._connected = False
            self._disconnected_at = time.monotonic()
            logger.warning("与 Discord 网关的连接已断开")

    async def on_resumed(self):
        """当 bot 通过 RESUME 成功恢复 Discord 会话时调用。"""
        self._connected = True
        self._disconnected_at = None
        logger.info("已恢复 Discord 会话")

    async def _heartbeat_writer(self):
        """后台任务：每 30 秒将健康状态写入心跳文件供 Docker healthcheck 读取。

        如果因事件循环阻塞导致此任务无法运行，文件将过期，
        Docker 可以独立检测到异常。
        """
        await asyncio.sleep(10)  # 等待 setup_hook 完成
        while not self.is_closed():
            try:
                state = {
                    "timestamp": time.time(),
                    "connected": self._connected,
                    "disconnected_since": (
                        # 将 monotonic 时钟转换为 wall-clock 时间戳，
                        # 使 healthcheck.py 能使用相同的 time.time() 基准正确计算断连时长
                        time.time() - (time.monotonic() - self._disconnected_at)
                        if self._disconnected_at is not None
                        else 0
                    ),
                    "is_closed": self.is_closed(),
                    "update_detector": self._get_update_detector_health(),
                }
                with open(self._heartbeat_path, "w", encoding="utf-8") as f:
                    json.dump(state, f)
            except Exception:
                logger.warning("写入心跳文件失败", exc_info=True)
            await asyncio.sleep(30)

    def _get_update_detector_health(self) -> dict[str, object]:
        """返回更新检测器的可用性元数据供健康诊断。"""
        cog = self.get_cog("UpdateDetector")
        if not isinstance(cog, UpdateDetector):
            return {"mode": "missing", "available": False}
        return {
            "mode": cog.mode,
            "available": cog.mode != "active" or cog.deepseek_service is not None,
            "reason": (
                "missing_deepseek_api_key"
                if cog.mode == "active" and cog.deepseek_service is None
                else None
            ),
        }

    async def _disconnect_timeout_monitor(self):
        """后台任务：若断连超过 5 分钟则主动退出进程。

        这是 Plan C（进程内自愈）的核心：当 discord.py 的重连循环
        持续失败时，以退出码 1 退出进程，由 Docker 的 unless-stopped
        策略自动重启容器。
        """
        await asyncio.sleep(120)  # 等待初始连接建立
        while not self.is_closed():
            if self._disconnected_at is not None:
                disconnected_for = time.monotonic() - self._disconnected_at
                if disconnected_for > self._max_disconnect_seconds:
                    logger.critical(
                        f"与 Discord 断开连接已持续 {disconnected_for:.0f} 秒"
                        f"（超过 {self._max_disconnect_seconds:.0f} 秒限制），"
                        "即将退出进程以触发 Docker 重启"
                    )
                    # 写入最终心跳供 Docker 诊断
                    try:
                        state = {
                            "timestamp": time.time(),
                            "connected": False,
                            "disconnected_since": self._disconnected_at,
                            "is_closed": True,
                        }
                        with open(self._heartbeat_path, "w", encoding="utf-8") as f:
                            json.dump(state, f)
                    except Exception:
                        pass
                    self._health_exit_code = 1
                    await self.close()
                    return
            await asyncio.sleep(30)

    # -------------------------
    # 生命周期
    # -------------------------

    async def close(self):
        """关闭机器人时，一并关闭调度器和数据库连接。

        可能被调用两次：一次由 _disconnect_timeout_monitor 主动退出，
        一次由 async with bot: 上下文管理器退出。通过 _closing 守卫
        保证内部清理逻辑只执行一次。
        """
        if self._closing:
            return
        self._closing = True
        await self.open_graph_reindex_consumer.stop()
        await self.impression_cache_service.stop()
        await self.api_scheduler.stop()
        await close_db()
        await super().close()

    # -------------------------
    # 辅助方法
    # -------------------------

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


async def main():
    # 配置日志记录
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        file_handler = TimedRotatingFileHandler(
            "/app/logs/bot.log", when="midnight", backupCount=7, encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
    except Exception:
        logging.getLogger().warning("无法创建日志文件处理器，仅输出到控制台")

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    intents.reactions = True

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # 启动时统一配置探索频道屏蔽列表，覆盖所有趋势写入路径。
    RedisTrendService.configure_ignored_channels(
        config.get("discovery", {}).get("ignore_channel_ids", [])
    )

    # 读取配置项并初始化全局Redis连接池
    redis_url = os.environ.get(
        "REDIS_URL", config.get("redis_url", "redis://odysseia-redis:6379/0")
    )
    await RedisManager.init_redis(redis_url)  # type: ignore[arg-type]

    # 清除上一次运行残留的就绪标志，确保 API 不会在 Bot 重启期间读到过期状态
    try:
        await RedisManager.get_client().delete("cache:forum-ready")
    except Exception:
        pass

    bot = MyBot(intents=intents, config=config)

    @bot.event
    async def on_ready():
        if bot.user:
            logger.info(f"机器人已登录: {bot.user} (ID: {bot.user.id})")
        else:
            logger.info("机器人已登录，但无法获取机器人信息。")

    try:
        async with bot:
            token = os.environ.get("BOT_TOKEN", "").strip()
            if not token:
                raise RuntimeError("BOT_TOKEN 环境变量未设置")
            await bot.start(token)  # type: ignore[arg-type]
    finally:
        # 服务关闭时切断与Redis的连接
        # 使用嵌套 try/finally 确保即使 close_redis() 抛出异常，
        # os._exit() 仍能执行并传播正确的退出码给 Docker
        try:
            await RedisManager.close_redis()
        finally:
            # 健康检测触发的退出，传播非零退出码让 Docker 感知
            if bot._health_exit_code:
                os._exit(bot._health_exit_code)


if __name__ == "__main__":
    import gc

    gc.freeze()
    gc.set_threshold(2000, 20, 20)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("机器人关闭。")
