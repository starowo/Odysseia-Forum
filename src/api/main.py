import json
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from .v1.routers import preferences, search, auth, follows, fetch_images, banner

# 读取配置
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    enable_docs = config.get("api", {}).get("enable_docs", True)
    
    # CORS配置：支持配置多个允许的源
    api_config = config.get("api", {})
    cors_origins = api_config.get("cors_origins", [])
    
    # 向后兼容：如果没有配置cors_origins，使用frontend_url
    if not cors_origins:
        frontend_url = config.get("auth", {}).get("frontend_url", "*")
        cors_origins = [frontend_url] if frontend_url else ["*"]
    
except (FileNotFoundError, KeyError):
    enable_docs = True
    cors_origins = ["*"]

# 根据配置决定是否启用文档
docs_url = "/docs" if enable_docs else None
redoc_url = "/redoc" if enable_docs else None

app = FastAPI(
    title="Odysseia Forum Bot API",
    description="Odysseia 论坛机器人 API 服务",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
)

# 配置 CORS
# 支持在config.json中配置多个允许的源
if "*" in cors_origins:
    # 允许所有源（不推荐用于生产环境）
    allowed_origins = ["*"]
    allow_credentials = False  # "*" 不能与 credentials 同时使用
else:
    # 使用配置的源列表
    allowed_origins = cors_origins
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],  # 允许所有headers
    expose_headers=["*"],  # 暴露所有headers
    max_age=3600,  # 预检请求缓存1小时
)

# 启用 GZip 压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 包含路由
app.include_router(auth.router, prefix="/v1")
app.include_router(preferences.router, prefix="/v1")
app.include_router(search.router, prefix="/v1")
app.include_router(follows.router, prefix="/v1")
app.include_router(fetch_images.router, prefix="/v1")
app.include_router(banner.router, prefix="/v1")


# 包含 v1 的健康检查端点
@app.get("/v1/health", summary="健康检查", tags=["系统"])
async def health_check():
    """API 服务健康检查端点"""
    return {"status": "ok"}


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
            "preferences": "/v1/preferences",
            "search": "/v1/search",
            "follows": "/v1/follows",
            "fetch-images": "/v1/fetch-images",
            "banner": "/v1/banner"
        },
    }
