# Odysseia Forum Search Bot

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://github.com/Rapptz/discord.py"><img src="https://img.shields.io/badge/discord.py-2.3+-5865F2.svg?style=flat&logo=discord&logoColor=white" alt="discord.py" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL" /></a>
  <a href="https://redis.io/"><img src="https://img.shields.io/badge/Redis-7-DC382D.svg?style=flat&logo=redis&logoColor=white" alt="Redis" /></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-✓-2496ED.svg?style=flat&logo=docker&logoColor=white" alt="Docker" /></a>
</p>

Discord 论坛搜索机器人，支持智能索引、多维度搜索、书单、收藏和用户偏好过滤。同时提供 FastAPI 搜索接口，供网页调用。

## 🌟 主要功能

### 📚 智能索引系统
- **批量构建**：支持对整个论坛频道（包括归档帖子）进行批量索引
- **实时更新**：监听已索引频道的帖子创建、更新、删除、标签、反应数等事件，从而自动更新索引

### 🔍 多维度搜索
- **标签搜索**：支持正选/反选模式，AND/OR逻辑
- **关键词搜索**：支持标题和内容搜索，AND/OR逻辑
- **作者过滤**：支持只看指定作者或屏蔽指定作者
- **范围过滤**：支持按发帖时间/活跃时间/反应数/发言数筛选
- **频道范围**：支持单频道或多频道搜索

### ⭐ 收藏与书单
- **帖子收藏**：收藏感兴趣的帖子，支持搜索和管理已收藏内容
- **书单系统**：创建自定义书单，支持公开/私密模式
- **赛事书单**：支持赛事型书单，关联参赛帖子与赛事讨论频道 (通过与赛事 BOT 的通信进行同步)

### 👤 用户偏好系统
- **搜索偏好**：保存用户的作者、时间、标签、关键词偏好
- **显示设置**：支持缩略图/大图预览模式
- **结果数量**：可自定义每页显示的搜索结果数量

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/warming-afternoon/Odysseia-Forum.git

cd Odysseia-Forum
```

### 2. 配置文件

```bash
cp config.example.json config.json
cp .env.example .env
```

编辑 `config.json` 和 `.env`，填入 Discord Bot Token、OAuth2 密钥等必要信息。

> 各配置项的详细说明请参阅 [配置指南](docs/CONFIGURATION.md)

### 3. Docker Compose 运行（推荐）

项目使用 PostgreSQL 作为数据库、Redis 作为缓存。Docker Compose 一键启动全部服务：

```bash
# 启动所有服务（PostgreSQL + Redis + Bot + API）
docker compose up -d --build
```

服务说明：

| 服务 | 端口 | 说明 |
|------|------|------|
| `odysseia-postgres` | 127.0.0.1:15432 | PostgreSQL 16 数据库 |
| `odysseia-redis` | 11810 | Redis 缓存 |
| `odysseia-forum-bot` | - | Discord 机器人 |
| `odysseia-forum-api` | 10810 | FastAPI 搜索接口 |

常用命令：

```bash
# 查看日志
docker compose logs -f

# 停止所有服务
docker compose down

# 停止并删除数据卷（⚠️ 会删除数据库数据）
docker compose down -v
```

### 4. 本地开发运行（不使用 Docker）

```bash
# 安装依赖
uv sync

# 确保 PostgreSQL 和 Redis 已运行，然后：
uv run bot_main.py    # 启动机器人
uv run api_main.py    # 启动 API 服务
```

## 📖 使用指南

### 基础设置

1. **邀请机器人**：确保机器人有以下权限：
   - 查看频道
   - 发送消息
   - 嵌入链接
   - 读取消息历史

2. **构建索引**：在论坛频道中使用 `/构建索引` 命令

3. **创建公开搜索** : 使用 `/创建公开全局搜索` 或 `/创建频道搜索` 命令，创建公开搜索面板

## 📝 命令列表

全部可用命令请参阅 [命令列表文档](docs/COMMANDS.md)

### 快速概览

**用户命令**：`/全局搜索` · `/搜索作者` · `/查看收藏` · 右键菜单 `搜索作品` / `收藏此帖` / `移除收藏`

**管理员命令**：`/构建索引` · `/移除索引` · `/创建公开全局搜索` · `/创建频道搜索` · `/配置` · `/banner`

## ⚙️ 排序算法

支持 **7 种排序方式**：综合排序 (UCB1) · 热门排序 (Reddit Hot) · 发帖时间 · 活跃时间 · 反应数 · 回复数 · 收藏数

> 各算法的详细说明与配置参数请参阅 [排序算法文档](docs/RANKING_ALGORITHM.md)

## 🌐 API 服务

项目提供基于 FastAPI 的 REST API，供配套前端及其他客户端调用。API 服务默认运行在 `10810` 端口。

- 配套前端项目：[Odysseia-Forum-webpage](https://github.com/shiyue137mh-netizen/Odysseia-Forum-webpage)
- 完整 API 文档：[src/api/README.md](src/api/README.md)

## 🏗️ 项目架构

> 完整架构说明与模块总览请参阅 [架构文档](docs/ARCHITECTURE.md)

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🐛 问题反馈

如果您遇到任何问题或有功能建议，请在 [Issues](https://github.com/warming-afternoon/Odysseia-Forum/issues) 页面提交。

---

**注意**：使用前请确保您已阅读Discord的服务条款和机器人使用政策。

