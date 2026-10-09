# 🧠 Core 模块

## 📖 简介
`core` 模块向下封装了与数据库的交互逻辑，向外封装了与 Discord 帖子的数据同步逻辑，并维护了高频访问数据 (tag/帖子/频道) 的内存缓存。

---

## 🏗️ 架构与设计原则

- Repositories (仓储层): 位于 `*_repository.py`，负责直接与数据库交互，封装增删改查 (CRUD) 逻辑，对外隐藏 SQL 细节。
- Services (业务服务层): 位于 `*_service.py`，负责外部 API 调用聚合，或管理长期驻留内存的后台任务。
- Caches (缓存层): 针对高频访问（如标签列表）或高频写入（如帖子浏览量）的数据，提供内存级别的缓冲，降低 SQLite 的 I/O 压力。

---

## 📂 目录结构与组件解析

### 1. 💾 数据库访问层 (Repositories)
*所有 Repository 都在初始化时接收一个 `AsyncSession` 对象。*

- `author_repository.py`: 作者信息的更新与统计 (发帖数、获赞数等)。
- `collection_repository.py`: 用户收藏夹管理，支持批量添加/移除，并联动 `RedisTrendService` 记录趋势。
- `config_repository.py`: 机器人全局配置 (`BotConfig`) 与互斥标签规则 (`MutexTag`) 的持久化。
- `follow_repository.py`: 帖子关注系统，处理自动关注、最后查看时间 (`last_viewed_at`) 及未读更新统计。
- `preferences_repository.py`: 用户的独立搜索偏好设置存取。
- `tag_repository.py`: 标签的创建、重命名、去重查询。
- `thread_repository.py`: 处理帖子数据的 Upsert、软删除 (`not_found_count`)、标签投票、活跃度更新以及复杂的多条件聚合统计。

### 2. ⚙️ 核心业务服务 (Services)
*Service 在初始化时接收 `session_factory` 以便自主管理事务，并接收 `bot` 实例以调用 API。*

- `sync_service.py`: 帖子数据抓取器。负责将 Discord 帖子同步到数据库。内置了**“重建帖”解析逻辑**。

### 3. ⚡ 内存缓存服务 (Caches)
- `cache_service.py`: 全局通用缓存。缓存已索引的频道列表、服务器结构以及 `BotConfig`，避免频繁查库。
- `tag_cache_service.py`: 标签缓存。维护 `Tag ID <-> Name` 的双向映射，以及全局合并标签列表，供自动补全和 UI 快速渲染使用。
- `impression_cache_service.py`: 异步展示次数缓冲池。利用内存计数器和锁收集短时间内的帖子曝光量，通过后台 Task 每隔一定时间批量 `UPDATE` 数据库。

---

## 💡 开发指南

### 帖子同步引擎 (`SyncService`)
当机器人监控到新帖子或收到同步指令时，会调用 `sync_thread`：
   - sync_thread自动提取帖子首楼内容 (`first_message_excerpt`) 和图片附件 (`thumbnail_urls`)。
   - 如果帖子首楼包含类似 `发帖人: <@ID>` 和 `补档: [链接]`，服务会将其识别为**重建帖**，通过请求指定的补档消息链接，将真正的作者和图片信息入库。
   - 如果是老帖子首次被索引，会自动触发 `_auto_follow_on_first_detect`，将帖子内的所有发言成员加入“关注列表”。

### Session 的生命周期管理
   - 如果你在写一个 `Repository` 的方法，**不要**在里面写 `async with session.begin():`。Session 的开启、提交 (`commit`) 或回滚 (`rollback`) 应该由调用端 (如 Cog 或 Service) 控制。
   - 例外情况：某些独立且封装完整的工具函数（如 `ImpressionCacheService.flush_to_db`），内部自行使用了 `session_factory()`。

### 软删除机制 (`not_found_count`)
   - 我们的系统在一次拉取同步失败时**不物理删除**帖子记录，以防是 API 抽风。
   - 当抓取不到帖子时，`thread_repository.increment_not_found_count` 会被调用。
   - 在编写任何面向用户展示的 SQL 过滤条件时，加上 `where(Thread.not_found_count == 0)` 和 `where(Thread.show_flag == True)`。

### 避免 UI 直接操作数据库
   - 如果你要在 UI 层新增一个业务逻辑，请先检查 `core` 里是否已经有对应的 Repository。如果没有，请在 Repository 中添加 SQL 方法，而不是在 `views` 里直接写 `select`。

### 缓存一致性
   - 当你在数据库中新增或修改了 `BotConfig` 或 `Tag`，记得触发事件或直接调用 `cache_service.build_or_refresh_cache()`，否则机器人的其他部分可能仍在使用旧的内存数据。
