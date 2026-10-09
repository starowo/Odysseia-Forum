# 🧭 Discovery 模块

## 📖 简介
`discovery` 模块为前端索引页提供 **发现页（Discovery Feed）** 数据服务。它整合多条内容轨道（最新、反应飙升、讨论飙升、收藏飙升），让用户无需主动搜索即可浏览当前热门和新鲜内容。

---

## 🏗️ 核心组件

### 1. `discovery_service.py` — 轨道编排服务
负责调度并聚合四条内容轨道：

| 轨道名称 | 数据来源 | 排序依据 |
|----------|----------|----------|
| `latest` | 数据库直接查询 | 帖子创建时间倒序 |
| `reaction_surge` | Redis 趋势服务 | 近 N 天反应数增量排名 |
| `discussion_surge` | Redis 趋势服务 | 近 N 天回复数增量排名 |
| `collection_surge` | Redis 趋势服务 | 近 N 天收藏数增量排名 |

**补偿机制**: 每条轨道在应用用户偏好过滤后，数据量可能不足。服务会自动进行最多 3 次补偿请求（逐步向后偏移），确保尽量填满每条轨道的展示数量。

### 2. `discovery_repository.py` — 数据访问层
封装发现页所需的底层查询：
- `get_latest_threads`: 按创建时间查询最新帖子。
- `get_threads_by_ids_ordered`: 根据 Redis 返回的 ID 列表，从数据库拉取帖子详情并保持原始排名顺序。
- `_apply_preferences_filter`: 应用用户搜索偏好（频道、标签、作者、关键词正反选）到查询中。

---

## 📂 目录结构

```text
discovery/
├── discovery_service.py     # 轨道编排：整合四条轨道 + 补偿请求。
└── discovery_repository.py  # 数据访问：底层查询 + 偏好过滤。
```

---

## ⚙️ 数据流

```
前端请求 → API (v1/routers/discovery.py)
         → DiscoveryService.get_discovery_rails()
             ├── _get_latest_threads_with_retry() → DiscoveryRepository → SQLite
             ├── _get_surge_threads_with_retry("reaction") → RedisTrendService → SQLite
             ├── _get_surge_threads_with_retry("reply") → RedisTrendService → SQLite
             └── _get_surge_threads_with_retry("collection") → RedisTrendService → SQLite
         → 返回 {latest, reaction_surge, discussion_surge, collection_surge}
```
