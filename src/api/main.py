import gc
import json
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from sqlalchemy import text

from api.middleware.rate_limit_middleware import RateLimitMiddleware
from api.v1.routers import (
    auth,
    author_follows,
    authors,
    banner,
    booklists,
    collections,
    fetch_images,
    follows,
    meta,
    notifications,
    open_graph,
    preferences,
    search,
    tags,
    discovery,
    tournaments,
)
from shared.database import AsyncSessionFactory
from shared.redis_client import RedisManager

logger = logging.getLogger(__name__)

# 读取配置
config = {}
api_config = {}
auth_config = {}
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    api_config = config.get("api", {})
    auth_config = config.get("auth", {})

    enable_docs = api_config.get("enable_docs", True)

    # 优先读取 api.cors_origins
    cors_origins = api_config.get("cors_origins", [])
    if isinstance(cors_origins, str):  # 防止有人填错成字符串
        cors_origins = [cors_origins]

    # 如果没配 cors_origins，尝试读取 auth.frontend_url
    frontend_url = auth_config.get("frontend_url")

    # 汇总允许的源
    allowed_origins = []
    if cors_origins:
        allowed_origins.extend(cors_origins)
    if frontend_url and frontend_url not in allowed_origins:
        allowed_origins.append(frontend_url)

    # 如果汇总后依然为空，则允许所有源
    if not allowed_origins:
        allowed_origins = ["*"]

except (FileNotFoundError, KeyError, json.JSONDecodeError):
    enable_docs = True
    allowed_origins = ["*"]

# 根据配置决定是否启用文档
docs_url = "/docs" if enable_docs else None
redoc_url = "/redoc" if enable_docs else None

app = FastAPI(
    title="Odysseia Forum Bot API",
    description="Odysseia 论坛机器人 API 服务",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    default_response_class=ORJSONResponse,
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
)

# 配置 CORS
# 支持在config.json中配置多个允许的源
if "*" in allowed_origins:
    # 允许所有源（不推荐用于生产环境）
    actual_allowed_origins = ["*"]
    allow_credentials = False  # "*" 不能与 credentials 同时使用
else:
    # 使用配置的源列表
    actual_allowed_origins = allowed_origins
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=actual_allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],  # 允许所有headers
    expose_headers=["*"],  # 暴露所有headers
    max_age=10800,  # 预检请求缓存3小时
)

# 全局限流中间件（CORS 之后、路由之前）
app.add_middleware(
    RateLimitMiddleware,
    config=api_config.get("rate_limit", {}).get("global", {}),
    jwt_secret=auth_config.get("jwt_secret"),
)

# 包含路由
app.include_router(auth.router, prefix="/v1")
app.include_router(authors.router, prefix="/v1")
app.include_router(author_follows.router, prefix="/v1")
app.include_router(preferences.router, prefix="/v1")
app.include_router(search.router, prefix="/v1")
app.include_router(follows.router, prefix="/v1")
app.include_router(notifications.router, prefix="/v1")
app.include_router(meta.router, prefix="/v1")
app.include_router(open_graph.router, prefix="/v1")
app.include_router(fetch_images.router, prefix="/v1")
app.include_router(banner.router, prefix="/v1")
app.include_router(collections.router, prefix="/v1")
app.include_router(booklists.router, prefix="/v1")
app.include_router(tags.router, prefix="/v1")
app.include_router(discovery.router, prefix="/v1")
app.include_router(tournaments.router, prefix="/v1")


# 包含 v1 的健康检查端点
@app.get("/v1/health", summary="健康检查", tags=["系统"])
async def health_check():
    """API 服务健康检查端点，检查数据库和 Redis 连通性"""
    healthy = True
    checks = {}

    # 数据库检查
    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        healthy = False
        logger.warning("健康检查：数据库不可达", exc_info=True)

    # Redis 检查
    try:
        redis = RedisManager.get_client()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
        healthy = False
        logger.warning("健康检查：Redis 不可达", exc_info=True)

    # Bot 元数据就绪检查（仅观测，不影响健康状态）
    try:
        redis = RedisManager.get_client()
        ready = await redis.get("cache:forum-ready")
        checks["bot_metadata"] = "ready" if ready else "not_ready"
    except Exception:
        checks["bot_metadata"] = "unknown"

    status_code = 200 if healthy else 503
    return JSONResponse(
        content={"status": "ok" if healthy else "degraded", "checks": checks},
        status_code=status_code,
    )


@app.get("/", summary="API 根路径", tags=["系统"])
async def root():
    """API 服务根路径"""
    return {
        "message": "Odysseia Forum Bot API",
        "version": "1.0.0",
        "v1_api": "/v1",
        "endpoints": {
            "health": "/v1/health",
            "auth": "/v1/auth",
            "authors": "/v1/authors",
            "preferences": "/v1/preferences",
            "search": "/v1/search",
            "follows": "/v1/follows",
            "meta": "/v1/meta",
            "fetch-images": "/v1/fetch-images",
            "banner": "/v1/banner",
            "collections": "/v1/collections",
            "booklists": "/v1/booklists",
            "tags": "/v1/tags",
        },
    }


@app.get("/v1/debug/memory", summary="内存诊断", tags=["系统"])
async def debug_memory():
    """调试端点：输出进程内存中 Top 对象类型及模块级内存占用"""
    # 对象类型统计（数量 + 大小）
    type_counts: dict[str, int] = {}
    type_sizes: dict[str, int] = {}
    module_sizes: dict[str, int] = {}
    module_counts: dict[str, int] = {}

    for obj in gc.get_objects():
        t = type(obj)
        name = t.__name__
        type_counts[name] = type_counts.get(name, 0) + 1

        try:
            sz = sys.getsizeof(obj)
        except Exception:
            sz = 0
        type_sizes[name] = type_sizes.get(name, 0) + sz

        mod = getattr(t, "__module__", None)
        if not isinstance(mod, str):
            mod = "builtins"
        parts = mod.split(".")
        prefix = ".".join(parts[:2]) if len(parts) >= 2 else mod
        module_sizes[prefix] = module_sizes.get(prefix, 0) + sz
        module_counts[prefix] = module_counts.get(prefix, 0) + 1

    # 按大小排序
    top_by_size = sorted(type_sizes.items(), key=lambda x: -x[1])[:20]
    top_by_count = sorted(type_counts.items(), key=lambda x: -x[1])[:20]
    top_modules = sorted(module_sizes.items(), key=lambda x: -x[1])[:20]

    # GC
    gc_stats = gc.get_stats()

    try:
        with open("/proc/self/status") as f:
            rss_line = [line for line in f if line.startswith("VmRSS:")]
        rss = rss_line[0].split()[1] if rss_line else "unknown"
    except Exception:
        rss = "unknown"

    return {
        "rss_kb": rss,
        "total_objects": sum(type_counts.values()),
        "total_size_kb": round(sum(type_sizes.values()) / 1024),
        "top_by_size": [
            {"type": t, "count": type_counts[t], "size_kb": round(s / 1024)}
            for t, s in top_by_size
        ],
        "top_by_count": [
            {"type": t, "count": c, "size_kb": round(type_sizes.get(t, 0) / 1024)}
            for t, c in top_by_count
        ],
        "modules_by_size_kb": [
            {
                "module": m,
                "objects": module_counts[m],
                "size_kb": round(s / 1024),
            }
            for m, s in top_modules
        ],
        "gc": {
            "generations": [
                {
                    "collections": s["collections"],
                    "collected": s["collected"],
                    "uncollectable": s["uncollectable"],
                }
                for s in gc_stats
            ],
            "thresholds": list(gc.get_threshold()),
        },
    }


@app.get("/v1/debug/memory/sources", summary="内存来源诊断", tags=["系统"])
async def debug_memory_sources():
    """调试端点：按模块来源汇总对象数量，定位泄漏代码路径"""
    module_counts: dict[str, int] = {}
    type_module_counts: dict[str, dict[str, int]] = {}
    total = 0

    for obj in gc.get_objects():
        total += 1
        cls = type(obj)
        type_name = cls.__name__
        try:
            module = getattr(cls, "__module__", None)
            if not isinstance(module, str) or not module:
                module = "builtins"
        except Exception:
            module = "builtins"
        # 截取到二级模块名
        parts = module.split(".")
        prefix = ".".join(parts[:2]) if len(parts) >= 2 else module
        module_counts[prefix] = module_counts.get(prefix, 0) + 1
        if prefix not in type_module_counts:
            type_module_counts[prefix] = {}
        type_module_counts[prefix][type_name] = (
            type_module_counts[prefix].get(type_name, 0) + 1
        )

    top_modules = sorted(module_counts.items(), key=lambda x: -x[1])[:20]
    sources = []
    for module, count in top_modules:
        types_in_module = sorted(
            type_module_counts[module].items(), key=lambda x: -x[1]
        )[:10]
        sources.append(
            {
                "module": module,
                "total_objects": count,
                "top_types": [{"type": t, "count": c} for t, c in types_in_module],
            }
        )

    return {"total_objects": total, "sources": sources}


@app.get("/v1/debug/memory/force-gc", summary="强制 GC 并对比", tags=["系统"])
async def debug_force_gc():
    """调试端点：强制全量 GC，对比回收前后的对象数和 RSS"""

    def _read_rss():
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1])
        except Exception:
            return -1

    rss_before = _read_rss()
    total_before = len(gc.get_objects())

    # 触发全量 GC
    collected = gc.collect(2)
    collected += gc.collect(1)
    collected += gc.collect(0)

    rss_after = _read_rss()
    total_after = len(gc.get_objects())

    return {
        "rss_kb_before": rss_before,
        "rss_kb_after": rss_after,
        "rss_freed_kb": rss_before - rss_after
        if rss_before > 0 and rss_after > 0
        else -1,
        "objects_before": total_before,
        "objects_after": total_after,
        "objects_freed": total_before - total_after,
        "gc_collected": collected,
        "interpretation": (
            "内存可回收，对象未释放 → 可能缺少 gc.collect() 调用"
            if total_before - total_after > 1000 and rss_before - rss_after > 1024
            else (
                "大量不可回收对象 → 循环引用被持有，或 C 扩展泄漏"
                if total_before - total_after < 100 and rss_before - rss_after < 1024
                else "GC 回收了小部分内存"
            )
        ),
    }


@app.get("/v1/debug/memory/pools", summary="连接池状态", tags=["系统"])
async def debug_pools():
    """调试端点：SQLAlchemy 连接池和 Redis 连接池状态"""
    pool = AsyncSessionFactory.kw["bind"].pool
    return {
        "sqlalchemy": {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.checkedin() + pool.checkedout(),
        },
    }
