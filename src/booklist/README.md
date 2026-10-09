# 📚 Booklist 模块

## 📖 简介
`booklist` 模块提供书单的业务逻辑服务层，负责协调书单表与帖子表之间的数据联动。核心职责是确保帖子的 **全局收藏计数** 在跨书单操作时保持正确（用户维度去重）。

---

## ⚙️ 核心机制

### 用户维度的收藏计数去重
一个用户可以创建多个书单，同一帖子可能被加入多个书单。但在帖子的 `collection_count`（全局被收藏数）统计中，同一用户只计一次。

**添加帖子时**:
1. 检查该帖子是否已存在于用户的其他书单中。
2. 只有"净增"（首次出现在该用户的任何书单中）的帖子才会增加 `collection_count`。
3. 对净增帖子同步上报 `RedisTrendService`（仅限近期发布的帖子，防止老帖屠榜）。

**移除帖子时**:
1. 执行移除操作后，检查该帖子是否仍存在于用户的其他书单中。
2. 只有"净减"（从所有书单中彻底消失）的帖子才会递减 `collection_count`。

---

## 📂 目录结构

```text
booklist/
├── __init__.py
└── booklist_service.py   # BooklistService: 书单添加/移除帖子、收藏计数联动。
```

---

## 💡 依赖关系
- `BooklistService` 由 `api` 模块的 `v1/routers/booklists.py` 调用。
- 底层依赖 `core/booklist_repository.py` 和 `core/thread_repository.py`。
