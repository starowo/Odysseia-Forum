# 配置指南

本项目需要两个配置文件：`config.json`（Bot 行为配置）和 `.env`（密钥与环境变量）。

## 快速上手

```bash
cp config.example.json config.json
cp .env.example .env
```

然后编辑两个文件，填入必要的值即可启动。

---

## config.json 配置项说明

### 最小可用配置

至少需要填写以下内容：

```json
{
  "token": "你的Discord Bot Token",
  "auth": {
    "client_id": "你的OAuth2客户端ID",
    "client_secret": "你的OAuth2客户端密钥",
    "redirect_uri": "https://你的域名/v1/auth/callback",
    "guild_id": "你的服务器ID",
    "jwt_secret": "一个长随机字符串",
    "bot_token": "你的Bot Token",
    "frontend_url": "https://你的前端域名"
  }
}
```

### 完整配置项

#### 基础设置

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `token` | string | Discord Bot Token（也可通过环境变量 `BOT_TOKEN` 设置） |
| `proxy` | string | HTTP 代理地址，留空则不使用代理 |
| `redis_url` | string | Redis 连接地址，Docker 部署默认 `redis://odysseia-redis:6379/0` |

#### 管理员与服务器

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `bot_admin_user_ids` | number[] | Bot 管理员用户 ID 列表 |
| `main_guild_id` | number | 主服务器 ID，留空则使用默认值 |
| `management_role_id` | number | 管理组身份组 ID，用于接收通知 |

#### 性能调优

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `performance.api_scheduler_concurrency` | number | 40 | 全局 Discord API 并发调用上限 |
| `performance.indexer_concurrency` | number | 10 | 索引模块的 API 并发调用上限 |

#### API 服务 (`api`)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `api.host` | string | `"0.0.0.0"` | 监听地址 |
| `api.port` | number | 10810 | 监听端口 |
| `api.enable_docs` | boolean | true | 是否启用 Swagger/ReDoc 文档 |
| `api.enable_ssl` | boolean | false | 是否启用 SSL |
| `api.ssl_cert_path` | string | — | SSL 证书路径 |
| `api.ssl_key_path` | string | — | SSL 私钥路径 |
| `api.cors_origins` | string[] | [] | CORS 允许的来源域名列表 |
| `api.api_key` | string | — | 机机通信 API Key（赛事等接口需要） |
| `api.rate_limit.search.max_requests` | number | 60 | 搜索接口每窗口最大请求数 |
| `api.rate_limit.similar.max_requests` | number | 60 | 相似推荐接口每窗口最大请求数 |
| `api.rate_limit.global.max_requests` | number | 300 | 已登录业务接口每分钟最大请求数 |
| `api.rate_limit.global.daily_watch_threshold` | number | 1500 | 服务器本地自然日请求数超过该值后启用并持续续期 Watch |

#### 认证 (`auth`)

> 用于 API 的 Discord OAuth2 登录与 JWT 鉴权。

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `auth.client_id` | string | Discord OAuth2 应用客户端 ID |
| `auth.client_secret` | string | Discord OAuth2 应用客户端密钥 |
| `auth.redirect_uri` | string | OAuth2 回调地址 |
| `auth.guild_id` | string | Discord 服务器 ID（用于校验用户身份） |
| `auth.role_ids` | string | 允许访问的身份组 ID，逗号分隔 |
| `auth.jwt_secret` | string | JWT 签名密钥（务必使用长随机字符串） |
| `auth.bot_token` | string | Bot Token（用于查询用户身份组） |
| `auth.frontend_url` | string | 前端地址（OAuth2 登录后重定向） |
| `auth.cookie_domain` | string | Cookie 域名（可选，留空使用默认） |

#### 频道映射 (`channel_mappings`)

将其他服务器的帖子映射为虚拟标签，搜索时可通过标签跨频道查找。

```json
"channel_mappings": {
  "目标频道ID": [
    {
      "tag_name": "虚拟标签名称",
      "source_channel_ids": ["来源频道ID1", "来源频道ID2"]
    }
  ]
}
```

#### 更新检测 (`update_detector`)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `update_detector.mode` | string | `"disabled"` | `disabled` 关闭、`observe` 本地估算、`active` 正式检测 |
| `update_detector.deepseek_base_url` | string | `"https://api.deepseek.com"` | DeepSeek 官方或兼容代理基础地址 |
| `update_detector.deepseek_model` | string | `"deepseek-v4-flash"` | 正式检测使用的模型 |
| `update_detector.thinking_enabled` | boolean | true | 是否开启 thinking 模式 |
| `update_detector.max_output_tokens` | number | 2048 | 单次最大生成 Token |
| `update_detector.request_timeout_seconds` | number | 60 | 请求超时时间（秒） |
| `update_detector.min_text_length` | number | 100 | 触发检测的最小文字长度 |
| `update_detector.min_text_length_with_attachment` | number | 30 | 带 PNG/JSON 附件时的最小文字长度 |

`observe` 模式不会请求 DeepSeek、发送提醒或同步数据库，只将本地 Token
估算按 UTC 日期写入 Redis。`active` 模式需要在 `.env` 中设置
`DEEPSEEK_API_KEY`。提醒消息仅帖子作者可操作，且不会自动删除。
修改 `mode` 后需要重启 Bot 容器，使更新检测模块重新加载配置。

查看最近七天的试监听统计：

```bash
docker compose exec odysseia-forum-bot \
  uv run python scripts/show_update_detector_stats.py --kind estimate --days 7
```

正式启用后将 `--kind` 改为 `actual` 即可查看真实 Token usage。也可使用
`--from YYYY-MM-DD --to YYYY-MM-DD` 指定日期范围，或用
`--format json` 输出 JSON。

统计按 UTC 日期存入 Redis Hash，代码固定保留 90 天：

```text
update_detector:token_stats:estimate:deepseek-v4-flash:YYYYMMDD
update_detector:token_stats:actual:deepseek-v4-flash:YYYYMMDD
```

`estimate` 保存潜在请求数、字符数、估算输入 Token 及 2048 Token 输出上界；
`actual` 保存请求成功/失败、YES/NO/无效判断数量及接口返回的真实输入、输出、
总 Token。统计中不保存消息正文、Discord ID、reasoning 或密钥。

#### 备份 (`backup`)

定时将数据库备份到 S3 兼容对象存储（如 Cloudflare R2）。

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `backup.enabled` | boolean | false | 是否启用自动备份 |

#### Banner 系统 (`banner`)

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `banner.enabled` | boolean | 是否启用 Banner 申请系统 |
| `banner.applicant_role_ids` | string | 允许申请的身份组 ID，逗号分隔 |
| `banner.review_thread_id` | number | 审核申请的 Thread ID |
| `banner.archive_thread_id` | number | 审核记录存档频道 ID |
| `banner.available_channels` | object | 可选展示频道列表 `{"频道ID": "名称"}` |

#### 深渊区 (`abyss`)

限制特定频道的帖子仅持有指定身份组的用户可见。

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `abyss.channel_ids` | number[] | 需要屏蔽的频道 ID 列表 |
| `abyss.required_role_id` | string | 允许查看的身份组 ID |

#### 广场推荐 (`discovery`)

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `discovery.ignore_channel_ids` | number[] | 不出现在探索推荐轨道及随机推荐中的频道 ID 列表；这些频道的帖子也不会新增写入 Redis 全局及频道趋势榜单，仍可正常索引和搜索 |

修改此列表后需重启 Bot 和 API 才能生效。此前已写入的 Redis 趋势数据自然过期，探索接口仍会过滤这些频道的帖子。

---

## .env 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `BOT_TOKEN` | 是 | Discord 机器人 Token（若 `config.json` 中未设置） |
| `PG_PASSWORD` | 否 | PostgreSQL 密码（Docker 部署默认 `changeme`） |
| `DATABASE_URL` | 否 | 完整数据库连接 URL（非 Docker 部署使用） |
| `DB_POOL_SIZE` | 否 | 数据库常驻连接数，默认 `5` |
| `DB_MAX_OVERFLOW` | 否 | 连接池临时溢出连接数，默认 `8` |
| `DB_POOL_TIMEOUT` | 否 | 获取连接的最长等待秒数，默认 `30` |
| `REDIS_URL` | 否 | 完整 Redis 连接 URL（非 Docker 部署使用） |
| `DEEPSEEK_API_KEY` | active 模式是 | DeepSeek API Key，仅供更新检测使用 |
| `BACKUP_ENCRYPTION_KEY` | 否 | 备份加密密钥（Base64 编码的 32 字节密钥） |

---

## 常见场景

### 仅使用 Bot，不需要 API

可以忽略 `auth` 和 `api` 配置段，仅配置 Bot Token 和基础项。

**Docker 部署**：只启动 Bot 相关服务，跳过 API 容器：

```bash
docker compose up -d odysseia-postgres odysseia-redis odysseia-forum-bot
```

**本地开发**：只运行 Bot，不启动 API：

```bash
uv run bot_main.py
```

### 需要网页访问 API

必须配置 `auth` 段并在 Discord 开发者后台创建 OAuth2 应用。

### 生产环境部署

- 设置 `api.enable_docs = false`
- 设置 `api.enable_ssl = true` 并配置证书路径
- 配置 `api.cors_origins` 为具体的前端域名
- 为 `auth.jwt_secret` 生成足够长的随机字符串
- 设置 `backup.enabled = true` 并配置 S3 存储
