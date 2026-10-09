# 🧵 ThreadManager 模块

## 📖 简介
`ThreadManager` 模块是 Discord 帖子生命周期管理的核心中枢。它监听 Discord 帖子事件（创建、更新、删除、消息、反应），实时维护数据库中帖子元数据的一致性，并实现互斥标签规则引擎和标签评价系统。

---

## 🏗️ 核心组件

### 1. `cog.py` — 模块入口与事件监听
ThreadManager Cog 注册了以下 Discord 事件监听器：

- `on_thread_create`: 新帖创建后延时 5 秒同步，应用互斥标签规则，自动关注贴主。
- `on_thread_member_join`: 用户加入帖子时自动添加关注记录。
- `on_thread_update`: 监听帖子标签或标题变更，触发互斥标签检查和数据重同步。
- `on_thread_delete`: 帖子被 Discord 物理删除时，同步清理数据库记录。
- `on_message`: 监听帖子内新消息，将回复数增量和活跃时间提交至 `BatchUpdateService`。
- `on_raw_message_edit`: 首楼编辑触发完整同步，其他消息编辑更新活跃时间。
- `on_raw_message_delete`: 首楼被删时隐藏帖子 (`show_flag=False`)，其他消息被删时记录减量。
- `on_raw_reaction_add/remove`: 首楼反应变化时更新帖子反应数统计，并向 Redis 趋势服务上报。

### 2. `thread_logic.py` — 业务逻辑处理器
将复杂的业务逻辑从 Cog 中抽离，包含：

- **互斥标签引擎** (`apply_mutex_tag_rules`): 检测帖子是否同时携带互斥标签，根据优先级规则或覆盖标签自动修正，并通过私信/帖内通知用户和管理组。
- **首楼删除处理** (`handle_first_message_deletion`): 将帖子标记为不可见，防止搜索到已失效的死链。
- **反应数补录** (`update_reaction_count_and_sync`): 更新反应数，如果记录不存在则触发完整同步。
- **标签预同步** (`pre_sync_forum_tags`): 索引前预写入论坛频道的所有可用标签。
- **发布更新** (`process_publish_update`): 贴主手动发布新章节/版本的指令逻辑。

### 3. `batch_update_service.py` — 批量更新服务
采用**内存缓冲 + 定时刷盘**模式，避免高频消息事件对 SQLite 的锁竞争：

- 在内存中累积帖子的回复增量和最后活跃时间。
- 每隔 N 秒（默认 30 秒）批量 `UPDATE` 到数据库。
- 如果发现数据库中不存在的帖子（幽灵数据），自动触发 `SyncService` 进行补录。
- 同时将有效帖子的回复增量同步至 `RedisTrendService`（飙升榜）。

### 4. `views/` — 交互视图
- `vote_view.py`: 标签评价面板，允许用户对帖子的各标签投赞/踩票。
- `visibility_view.py`: 帖子可见性切换按钮（持久化视图），允许贴主在首楼被删后手动恢复搜索可见性。

---

## 📂 目录结构

```text
ThreadManager/
├── cog.py                    # 模块入口，事件监听器注册。
├── thread_logic.py           # 核心业务逻辑（互斥标签、删除处理等）。
├── batch_update_service.py   # 后台批量更新服务（内存缓冲 + 定时刷盘）。
├── update_data_dto.py        # 内部 DTO，定义更新数据的结构。
└── views/
    ├── vote_view.py          # 标签评价 UI。
    └── visibility_view.py    # 帖子可见性恢复按钮（持久化视图）。
```

---

## ⚙️ 核心机制

### 互斥标签规则引擎
当帖子被创建或标签被修改时：
1. 从数据库加载所有互斥标签组及其优先级规则。
2. 检测帖子当前标签是否有组内冲突。
3. 若存在冲突：
   - 有覆盖标签 → 移除所有冲突标签，应用覆盖标签。
   - 无覆盖标签 → 保留优先级最高的标签，移除其余。
4. 通过 `api_scheduler` 修改 Discord 帖子标签。
5. 向用户发送私信通知（失败则在帖内公开通知），可选通知管理组。

### 批量更新的幽灵数据检测
当 `batch_update` 写入数据库后，如果受影响行数少于预期：
1. 比对提交的 ID 和数据库中实际存在的 ID。
2. 差集即为"幽灵数据"（频道内有活动但尚未被索引的帖子）。
3. 为每个幽灵帖子在后台触发一次低优先级的完整同步。
