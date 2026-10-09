# ⚙️ Config 模块

## 📖 简介
`config` 模块提供机器人的 **运行时配置管理** 功能，允许管理员通过 Discord 斜杠命令在线调整 Bot 参数（如 UCB1 权重、全局配置项）和互斥标签规则，无需重启服务。

---

## 🏗️ 核心组件

### 1. `cog.py` — 模块入口
注册 `/配置` 命令组，所有命令均需管理员或 Bot 管理员权限：
- `/配置 全局设置`: 打开通用配置面板（UCB1 参数、探索因子等）。
- `/配置 互斥标签组`: 打开互斥标签组配置面板。
- `/配置 重载配置`: 重新加载 `config.json` 文件。
- `/配置 刷新缓存`: 手动刷新标签缓存、频道缓存和 BotConfig 缓存。

同时监听 `on_config_updated` 事件，当配置被修改时自动刷新内存缓存。

### 2. `general_config_handler.py` — 通用配置处理器
负责将 `BotConfig` 表中的键值对渲染为交互式面板，允许管理员在线修改各项数值参数。

### 3. `mutex_tags_handler.py` — 互斥标签配置处理器
管理互斥标签组的创建、编辑、删除：
- 展示当前所有互斥组及其规则。
- 支持添加新组、设定组内标签优先级、配置覆盖标签。
- 支持开关管理组通知。

### 4. `embed_builder.py` — Embed 构建工具
将配置数据格式化为 Discord Embed 展示。

### 5. `views/` — 交互视图
- `config_panel_view.py`: 通用配置面板视图。
- `mutex_config_view.py`: 互斥标签组列表视图。
- `add_mutex_group_view.py`: 新增/编辑互斥标签组的完整交互流程。

---

## 📂 目录结构

```text
config/
├── cog.py                      # 命令注册、权限检查、事件监听。
├── general_config_handler.py   # BotConfig 通用参数配置处理。
├── mutex_tags_handler.py       # 互斥标签组 CRUD 逻辑。
├── embed_builder.py            # 配置 Embed 格式化。
└── views/
    ├── config_panel_view.py    # 通用配置面板 UI。
    ├── mutex_config_view.py    # 互斥标签组列表 UI。
    ├── add_mutex_group_view.py # 新增/编辑互斥组流程 UI。
    └── components/             # 可复用的 UI 子组件。
```
