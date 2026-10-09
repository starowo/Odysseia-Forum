# 🧰 Shared 模块 (全局共享工具与基础组件)

## 📖 简介
`shared` 模块是本 Discord BOT 的 **基础设施与通用工具库**。

将本模块独立出来的主要目的是 消除代码重复 并 避免循环依赖。

如果你编写了一个函数、UI 组件或枚举，并且它 **被两个或以上的独立业务模块所使用**，那么它就应该被放置在 `shared` 模块中。

---

## 📂 目录结构与核心组件

```text
shared/
├── api_scheduler.py             # 🚦 Discord API 全局调度与限流器。
├── database.py                  # 🗄️ 数据库引擎、FTS5 初始化与触发器管理。
├── redis_client.py              # 🔴 全局 Redis 连接池管理器。
├── fts5_tokenizer.py            # SQLite FTS5 与 Jieba-rs 结巴分词的底层粘合层。
│
├── safe_defer.py                # Discord 交互响应保护工具 (`safe_defer`)。
├── discord_utils.py             # 封装高频的 Discord API 安全调用 (如获取用户)。
│
├── keyword_parser.py            # 高级搜索语法解析器 (处理 author:, "", - 语法)。
├── range_parser.py              # 数学区间字符串解析器 (如 "[10, 100)")。
├── time_parser.py               # 相对/绝对时间解析器 (如 "-7d", "2023-01-01")。
│
├── exceptions.py                # 全局自定义异常定义。
├── utils.py                     # 杂项通用纯函数。
│
├── enum/                        # 🏷️ 枚举定义目录 (消除魔法数字/字符串)
│   ├── application_status.py    # Banner 申请状态枚举。
│   ├── collection_type.py       # 收藏目标类型枚举 (Thread/Booklist)。
│   ├── constant_enum.py         # 业务相关常量 (如趋势数据缓存天数)。
│   ├── default_preferences.py   # 搜索偏好的默认值。
│   └── search_config_type.py    # UCB1 算法等配置类型的枚举。
│
└── views/                       # 🧩 全局通用 UI 组件
    ├── tag_select.py            # 通用标签多选/分页下拉框。
    └── components/
        ├── page_jump_modal.py   # 通用页码跳转输入模态框。
        └── time_range_modal.py  # 通用时间范围输入模态框。
```

---

## ⚙️ 核心基础设施说明

### 1. Discord API 调度器 (`APIScheduler`)
由于 Discord 严格的速率限制（Rate Limits），直接并发调用 API（如批量拉取帖子、获取用户）可能导致 Bot 被封禁。
`APIScheduler` 实现了一个**带优先级的令牌桶/信号量机制**：
- 用户触发的 UI 交互拥有**高优先级** (Priority 1-4)。
- 后台批量扫描/索引任务拥有**低优先级** (Priority 8-10)。
**规范**：高频 api 调用模块(例如 search 模块)中，主动向 Discord 发起的 API 请求，都应该通过调度器提交：
```python
user = await bot.api_scheduler.submit(
    coro_factory=lambda: bot.fetch_user(user_id),
    priority=5
)
```

### 2. 数据库引擎配置 (`database.py`)
这里初始化了 SQLAlchemy 的 `AsyncEngine` 和 `session_factory`。
**机制**：
- 开启了 SQLite 的 `WAL` (Write-Ahead Logging) 模式，极大提升并发读写性能。
- 在每次连接 (connect 事件) 时，会自动通过 `register_jieba_tokenizer` 挂载结巴分词器，确保 FTS5 全文搜索在异步环境下可用。
- 包含了 SQLite 触发器 (`CREATE TRIGGER`)，确保 `Thread` 表的增删改会自动同步到 `thread_fts` 虚拟表。

### 3. 安全的交互响应 (`safe_defer.py`)
Discord 要求机器人必须在 **3秒内** 响应用户的操作（按钮、下拉框、命令）。当遇到需要查询数据库或请求 API 的耗时操作时，必须先占位 (`defer`)。
直接调用 `interaction.response.defer()` 在并发极高时可能会抛出 `InteractionResponded` 异常。
**规范**：耗时操作前统一使用：
```python
from shared.safe_defer import safe_defer
await safe_defer(interaction, ephemeral=True)
```

### 4. 解析器组 (`*_parser.py`)
为了统一用户输入体验并防止注入，系统提供了多个解析器：
- `KeywordParser`: 剥离特殊搜索语法（排除词、精确匹配），确保生成的 SQL FTS 语法安全。
- `RangeParser`: 将用户输入的 `[10, 50)` 转换为 `min_val, max_val, min_op, max_op`。
- `TimeParser`: 支持 `YYYY-MM-DD` 和自然的相对时间（如 `-3d`, `-1w`），统一输出 UTC 时区的 `datetime` 对象。

---

## 🛠️ 开发准则

### 🚫 1. 绝对禁止反向依赖
`shared` 模块位于依赖树的**最底层**。
**规则**：`shared` 目录下的任何文件，**绝对不允许** `import` 来自 `core`、`search`、`indexing` 等上层模块的代码。
如果你发现在 `shared` 中需要引入上层模块，说明这个逻辑 **不属于** `shared`，请将其移回具体的业务模块中，或者使用依赖注入、回调函数、事件分发 (`bot.dispatch`) 来解耦。

### ✨ 2. 无状态性
`shared` 中的工具函数（如 `utils.py`、`discord_utils.py` 和各类 Parser）应该是**无状态的纯函数**。除了 `APIScheduler` 和 `RedisManager` 这种明确作为基础设施单例运行的类之外，不要在 `shared` 中维护全局变量或复杂的业务状态。

### 🏷️ 3. 告别魔法值
如果你的代码中出现了诸如 `status == 1`、`type == "pending"` 这样的逻辑，请立刻停止。
将其提取到枚举类中。这不仅有助于类型提示，还能在跨模块调用时保持含义一致。
