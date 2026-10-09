import asyncio
import json
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

import uvicorn
from dotenv import load_dotenv

import booklist.booklist_service as booklist_service_module
from api.main import app as fastapi_app
from api.v1.dependencies.rate_limit import initialize_rate_limit
from api.v1.dependencies.security import initialize_api_security
from core.api_cache_service import ApiCacheService
from core.redis_trend_service import RedisTrendService
from core.impression_cache_service import ImpressionCacheService
from core.tag_cache_service import TagCacheService
from search.similar_threads_cache_service import SimilarThreadsCacheService
from shared.database import AsyncSessionFactory, close_db, init_db
from shared.enum import AbyssDefaults, SearchConfigDefaultsInt
from shared.redis_client import RedisManager
from tag.tag_runtime import create_tag_mediator
from api.v1.routers import (
    preferences as preferences_api,
    search as search_api,
    meta as meta_api,
    open_graph as open_graph_api,
    fetch_images as fetch_images_api,
    banner as banner_api,
    tags as tags_api,
    discovery as discovery_api,
    booklists as booklists_api,
    follows as follows_api,
)
from api.v1.routers.auth import initialize_auth_config

load_dotenv()

if sys.platform != "win32":
    try:
        import uvloop

        uvloop.install()
        print("uvloop 已启用。")
    except ImportError:
        print("未找到 uvloop，将使用默认的 asyncio 事件循环。")

logger = logging.getLogger(__name__)


def _inject_api_dependencies(
    cache_service: ApiCacheService,
    tag_cache_service: TagCacheService,
    impression_cache_service: ImpressionCacheService,
    similar_threads_cache_service: SimilarThreadsCacheService,
    config: dict,
):
    """向 API 路由模块注入运行期依赖。"""

    main_guild_id = _get_main_guild_id_from_config(config)
    tags_api.event_mediator = create_tag_mediator(
        AsyncSessionFactory, config, RedisManager.get_client()
    )

    preferences_api.async_session_factory = AsyncSessionFactory
    preferences_api.main_guild_id = main_guild_id

    meta_api.cache_service_instance = cache_service
    meta_api.role_config = {**config, "main_guild_id": main_guild_id}

    search_api.async_session_factory = AsyncSessionFactory
    search_api.cache_service_instance = cache_service
    search_api.tag_cache_service_instance = tag_cache_service
    search_api.impression_cache_service_instance = impression_cache_service
    search_api.similar_threads_cache_service_instance = similar_threads_cache_service
    search_api.main_guild_id = main_guild_id

    tags_api.async_session_factory = AsyncSessionFactory
    tags_api.cache_service_instance = cache_service

    discovery_api.async_session_factory = AsyncSessionFactory
    discovery_api.main_guild_id = main_guild_id
    discovery_api.cache_service_instance = cache_service

    follows_api.cache_service_instance = cache_service

    banner_api.async_session_factory = AsyncSessionFactory
    banner_api.banner_config = config.get("banner", {})
    banner_api.main_guild_id = main_guild_id
    banner_api.tag_cache_service_instance = tag_cache_service
    bot_token = os.environ.get("BOT_TOKEN", "").strip()
    banner_api.bot_token = bot_token

    channel_mappings_config = _build_channel_mappings_config(config)
    search_api.channel_mappings_config = channel_mappings_config
    meta_api.channel_mappings_config = channel_mappings_config
    tags_api.channel_mappings_config = channel_mappings_config
    discovery_api.channel_mappings_config = channel_mappings_config
    booklists_api.channel_mappings_config = channel_mappings_config
    follows_api.channel_mappings_config = channel_mappings_config
    banner_api.channel_mappings_config = channel_mappings_config

    # 注入书单发布配置
    publish_cfg = config.get("integration", {}).get("booklist_publish", {})
    booklists_api._booklist_publish_base_url = publish_cfg.get("base_url", "")
    booklists_api._booklist_publish_api_key = publish_cfg.get("api_key", "")

    booklist_service_module._booklist_publish_base_url = publish_cfg.get("base_url", "")
    booklist_service_module._booklist_publish_api_key = publish_cfg.get("api_key", "")

    raw_abyss = config.get("abyss", {}) if isinstance(config, dict) else {}
    abyss_config = {
        "channel_ids": raw_abyss.get("channel_ids", AbyssDefaults.CHANNEL_IDS),
        "required_role_id": raw_abyss.get(
            "required_role_id", AbyssDefaults.REQUIRED_ROLE_ID
        ),
    }
    search_api.abyss_config = abyss_config
    discovery_api.abyss_config = abyss_config
    tags_api.abyss_config = abyss_config

    # 广场推荐忽略频道配置
    raw_discovery = config.get("discovery", {}) if isinstance(config, dict) else {}
    discovery_ignore_channel_ids = RedisTrendService.configure_ignored_channels(
        raw_discovery.get("ignore_channel_ids", [])
    )
    discovery_api.discovery_ignore_channel_ids = discovery_ignore_channel_ids

    auth_section = config.get("auth", {}) if isinstance(config, dict) else {}
    fetch_images_api.configure_fetch_images_router(
        session_factory=AsyncSessionFactory,
        bot_token=bot_token,
        guild_id=auth_section.get("guild_id"),
    )

    open_graph_config = config.get("integration", {}).get("open_graph", {})
    open_graph_api.configure_open_graph_router(
        session_factory=AsyncSessionFactory,
        redis=RedisManager.get_client(),
        config=open_graph_config,
        abyss_config=abyss_config,
    )

    logger.info("API 路由服务注入完成")


def _build_channel_mappings_config(config: dict) -> dict[int, list[dict]]:
    """将配置中的频道映射转换为 API 路由可直接使用的结构"""
    raw_mappings = config.get("channel_mappings", {})
    parsed_mappings = {}
    for key, val in raw_mappings.items():
        if key.startswith("_"):
            continue
        if not isinstance(val, list):
            continue
        try:
            ch_id = int(key)
        except (ValueError, TypeError):
            continue
        parsed_mappings[ch_id] = [
            {
                "tag_name": mapping["tag_name"],
                "source_channel_ids": [
                    int(channel_id)
                    for channel_id in mapping.get("source_channel_ids", [])
                ],
            }
            for mapping in val
            if isinstance(mapping, dict) and "tag_name" in mapping
        ]
    return parsed_mappings


def _get_main_guild_id_from_config(config: dict) -> int:
    """从配置文件读取主服务器 ID；为空时回退到默认值。"""
    raw_main_guild_id = config.get("main_guild_id")
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
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        file_handler = TimedRotatingFileHandler(
            "/app/logs/api.log", when="midnight", backupCount=7, encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
    except Exception:
        logging.getLogger().warning("无法创建日志文件处理器，仅输出到控制台")

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # 初始化 Redis
    redis_url = config.get("redis_url", "redis://odysseia-redis:6379/0")
    await RedisManager.init_redis(redis_url)

    # 初始化数据库
    await init_db()

    # 初始化安全与认证配置
    initialize_api_security()
    initialize_auth_config()

    # 初始化频率限制配置
    initialize_rate_limit(config)

    # 创建并构建缓存服务
    cache_service = ApiCacheService(
        session_factory=AsyncSessionFactory,
        redis_client=RedisManager.get_client(),
    )
    await cache_service.build_cache()
    cache_service.start()

    tag_cache_service = TagCacheService(AsyncSessionFactory)
    await tag_cache_service.build_cache()

    impression_cache_service = ImpressionCacheService(
        session_factory=AsyncSessionFactory,
    )
    impression_cache_service.start()

    similar_threads_cache_service = SimilarThreadsCacheService(
        RedisManager.get_client()
    )

    # 注入依赖到 API 路由模块
    _inject_api_dependencies(
        cache_service=cache_service,
        tag_cache_service=tag_cache_service,
        impression_cache_service=impression_cache_service,
        similar_threads_cache_service=similar_threads_cache_service,
        config=config,
    )

    # 启动 uvicorn API 服务器
    api_config = config.get("api", {})
    uvicorn_config = uvicorn.Config(
        app=fastapi_app,
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 10810),
        log_level="warning",
        proxy_headers=True,
        forwarded_allow_ips="*",
        ssl_keyfile=api_config.get("ssl_key_path", None)
        if api_config.get("enable_ssl", False)
        else None,
        ssl_certfile=api_config.get("ssl_cert_path", None)
        if api_config.get("enable_ssl", False)
        else None,
    )
    server = uvicorn.Server(uvicorn_config)
    try:
        await server.serve()
    finally:
        # 清理
        await similar_threads_cache_service.close()
        await impression_cache_service.stop()
        await cache_service.stop()
        await close_db()
        await RedisManager.close_redis()


if __name__ == "__main__":
    import gc

    gc.freeze()
    gc.set_threshold(2000, 20, 20)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("API 服务关闭。")
