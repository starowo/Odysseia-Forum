# ⭐ Collection 模块

## 📖 简介
`collection` 模块处理用户在 Discord 内的 **帖子收藏** 功能。通过右键上下文菜单，用户可以快速收藏或取消收藏帖子，系统会自动维护帖子的全局收藏计数。

---

## 🏗️ 核心组件

### 1. `cog.py` — 模块入口
- 注册两个右键上下文菜单命令：`⭐ 收藏此帖` 和 `➖ 移除收藏`。
- 加载内部事件监听器 Cog。
- 收藏/取消时通过事件 (`thread_collection_updated`) 通知统计监听器异步更新帖子的全局收藏数。

### 2. `listeners.py` — 批量操作事件监听器
监听来自其他视图的事件，启动批量收藏/取消收藏的交互 UI：
- `on_show_batch_collect_view`: 展示"已关注但未收藏"的帖子批量收藏面板。
- `on_show_batch_uncollect_view`: 展示已收藏帖子的批量取消面板。

### 3. `stats_listener.py` — 统计异步更新器
- 监听 `on_thread_collection_updated` 事件。
- 接收已完成用户维度去重判定的帖子 ID 列表和变化量 (delta)。
- 异步批量更新数据库中的帖子 `collection_count` 字段。

### 4. `views/` — 交互视图
- `base_management_view.py`: 批量操作视图的抽象基类（分页、全选、确认逻辑）。
- `batch_collect_view.py`: 批量收藏视图实现。
- `batch_uncollect_view.py`: 批量取消收藏视图实现。
- `confirmation_view.py`: 确认对话框。
- `thread_select.py`: 帖子多选下拉框组件。

---

## 📂 目录结构

```text
collection/
├── cog.py                        # 入口：右键菜单注册、监听器加载。
├── listeners.py                  # 批量操作事件监听（显示批量收藏/取消视图）。
├── stats_listener.py             # 统计更新事件监听（异步更新收藏计数）。
└── views/
    ├── base_management_view.py   # 批量操作抽象基类。
    ├── batch_collect_view.py     # 批量收藏 UI。
    ├── batch_uncollect_view.py   # 批量取消收藏 UI。
    ├── confirmation_view.py      # 确认对话框。
    └── thread_select.py          # 帖子选择组件。
```

---

## ⚙️ 核心机制

### 收藏计数的用户维度去重
与 `booklist` 模块类似，收藏操作时会判断用户是否已在其他途径（如书单）收藏过该帖：
- **收藏时**: 仅当帖子首次出现在该用户的收藏体系中时，才 dispatch `thread_collection_updated` 事件（delta=+1）。
- **取消时**: 底层执行的是"从所有收藏记录中移除"，因此一旦成功必然是净减（delta=-1）。
