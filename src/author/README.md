# 👤 Author 模块

## 📖 简介
`author` 模块负责 Discord 用户信息的异步拉取与入库。由于 Discord API 的速率限制，用户信息不能在帖子同步时同步获取，因此采用 **Redis 队列 + 定时消费** 的异步架构。

---

## ⚙️ 核心工作原理

### 异步拉取队列
1. 当其他模块（如 `SyncService`）发现帖子作者信息缺失或过期时，将 `user_id` 压入 Redis 集合 `author_fetch_queue`。
2. `AuthorCog` 每 **10 分钟** 运行一次定时任务，从 Redis 集合中原子弹出最多 50 个 ID。
3. 逐个调用 Discord API 拉取用户信息（`name`、`global_name`、`display_name`、`avatar_url`），并 Upsert 到数据库。
4. 每次拉取间隔 1.5 秒，避免触发 API 限流。

### 容错机制
- **拉取失败但用户已在库**: 仅更新 `last_updated` 时间戳，防止该用户被反复入队。
- **拉取失败且用户不在库**: 写入一条占位数据（`未知用户{id}`），同样防止无效循环拉取。

---

## 📂 目录结构

```text
author/
├── __init__.py
└── cog.py       # AuthorCog：定时任务、Redis 队列消费、用户信息入库逻辑。
```
