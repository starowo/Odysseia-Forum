# 后端数据概览（生产环境）

本文件基于后端实际代码整理，用于说明 **生产环境** 中前端能够从 API 拿到的字段与含义。

> 代码参考：
- `src/api/v1/routers/search.py`
- `src/api/v1/routers/meta.py`
- `src/api/v1/routers/preferences.py`
- `src/api/v1/schemas/search/search_request.py`
- `src/api/v1/schemas/search/search_response.py`
- `src/api/v1/schemas/meta/channel.py`
- `src/api/v1/schemas/meta/tag_detail.py`
- `src/api/v1/schemas/preferences/user_preferences.py`
- `src/api/v1/schemas/banner/banner_item.py`
- `src/shared/models/thread.py`

## 1. 通用约定

- API 前缀：`/v1`
- 所有接口默认在 HTTP 层使用 JSON。
- 鉴权：
  - 搜索与偏好接口依赖 `require_auth` / `get_current_user`，需要携带有效的 Bearer Token。
- ID 序列化：
  - 线程 ID、频道 ID、Banner 中的 `thread_id` / `channel_id` 等字段在模型内部是 `int`，
  - 通过 Pydantic 的 `field_serializer` 转成 **字符串** 返回前端，避免 JavaScript 精度问题。
- 分页：
  - 使用 `limit` + `offset` 模式，响应中会返回 `total`、`limit`、`offset`。

## 2. 搜索接口 `/v1/search`

路由定义见 `src/api/v1/routers/search.py`：

- 方法：`POST /v1/search/`
- 依赖：`require_auth`（需要登录态）
- 请求体：`SearchRequest`
- 响应体：`SearchResponse`（包含 `ThreadDetail` 列表、标签、Banner、未读数等）

### 2.1 SearchRequest 请求字段

定义见 `src/api/v1/schemas/search/search_request.py`：

- `channel_ids: Optional[List[int]]`
  - 要搜索的频道 ID 列表，为空则搜索所有已索引频道。
- `include_tags: List[str]`
  - 必须包含的标签名列表。
- `exclude_tags: List[str]`
  - 必须排除的标签名列表。
- `tag_logic: str`
  - 多标签逻辑：`"and"`（全部命中）或 `"or"`（任意命中）。
- `keywords: Optional[str]`
  - 搜索关键词，支持逗号（AND）与斜杠（OR）组合。
- `exclude_keywords: Optional[str]`
  - 要排除的关键词，使用逗号分隔。
- `exclude_keyword_exemption_markers: Optional[List[str]]`
  - 关键词排除豁免标记，包含这些标记的反选关键词不会被排除。
- `include_authors: Optional[List[int]]`
  - 只看这些作者的帖子（作者 ID 列表）。
- `exclude_authors: Optional[List[int]]`
  - 屏蔽这些作者的帖子。
- `author_name: Optional[str]`
  - 模糊搜索作者全局昵称或用户名。
- `created_after / created_before: Optional[str]`
  - 发帖时间范围，支持绝对日期（`YYYY-MM-DD`）或相对时间（如 `-7d`）。
- `active_after / active_before: Optional[str]`
  - 最后活跃时间范围，规则同上。
- `reaction_count_range: str`
  - 点赞数范围，默认来自 `DefaultPreferences.DEFAULT_NUMERIC_RANGE`，如 `">10"`、`"5-20"`。
- `reply_count_range: str`
  - 回复数范围，例如 `">=5"`。
- `sort_method: str`
  - 排序方法：
    - `"comprehensive"`：综合排序（默认）
    - `"created_at"`：发帖时间
    - `"last_active"`：最后活跃时间
    - `"reaction_count"`：点赞数
    - `"reply_count"`：回复数
    - `"custom"`：自定义排序
- `custom_base_sort: str`
  - 当 `sort_method = "custom"` 时使用的基础排序算法，默认 `"comprehensive"`。
- `sort_order: str`
  - 排序顺序：`"asc"` 或 `"desc"`，默认 `"desc"`。
- `limit: int`
  - 每页返回数量，范围 1–100，默认 10。
- `offset: int`
  - 偏移量，从 0 开始。

> 生产环境中，`search.py` 还会通过 `KeywordParser` 对 `keywords` 做二次解析，抽取作者名、精确关键词与排除词，组合成实际用于检索的 `final_keywords` 和 `final_exclude_keywords`。

### 2.2 SearchResponse 响应字段

定义见 `src/api/v1/schemas/search/search_response.py`。该响应继承自 `PaginatedResponse[ThreadDetail]`，并增加了若干额外字段。

基础分页字段：

- `total: int`
- `limit: int`
- `offset: int`

#### 2.2.1 ThreadDetail 帖子字段

`ThreadDetail` 是搜索结果中单个帖子的公开视图，其字段主要来自 `src/shared/models/thread.py`：

- `thread_id: str`
  - 帖子的 Discord ID（以字符串形式返回）。
- `channel_id: str`
  - 所在频道的 Discord ID（字符串）。
- `title: str`
  - 帖子标题。
- `author: Optional[AuthorDetail]`
  - 帖子作者详细信息，包括作者 ID、用户名、头像等。
- `created_at: datetime`
  - 创建时间。
- `last_active_at: Optional[datetime]`
  - 最后活跃时间（例如最新回复或更新）。
- `reaction_count: int`
  - 点赞数 / 表情反应数。
- `reply_count: int`
  - 回复数。
- `display_count: int`
  - 在搜索结果中展示的次数（用于排序算法统计）。
- `first_message_excerpt: Optional[str]`
  - 首条消息摘要。
- `thumbnail_url: Optional[str]`
  - 缩略图 URL（如首张图片或配置的封面）。
- `tags: List[str]`
  - 帖子关联标签名称列表。

#### 2.2.2 扩展字段

除了 `results: List[ThreadDetail]` 外，`SearchResponse` 还包含：

- `available_tags: List[str]`
  - 当搜索 **单个频道** 时，返回该频道的可用标签名列表。
  - 全频道搜索时为空列表。
- `banner_carousel: List[BannerItem]`
  - 当前频道以及全局可展示的 Banner 列表，最多 8 个。
  - `BannerItem` 字段：
    - `thread_id: str`
    - `title: str`
    - `cover_image_url: str`
    - `channel_id: str`
- `unread_count: int`
  - 当前用户关注列表中的未读更新数量（由 `FollowService.get_unread_count` 统计）。

## 3. 元数据接口 `/v1/meta/channels`

路由定义见 `src/api/v1/routers/meta.py`：

- 方法：`GET /v1/meta/channels`
- 依赖：`get_current_user`（需要登录态）
- 查询参数：
  - `channel_ids: Optional[List[int]]`：可选的频道 ID 列表，缺省时返回所有已索引频道。
- 响应体：`List[Channel]`

`Channel` 定义见 `src/api/v1/schemas/meta/channel.py`：

- `id: int`
  - 频道 Discord ID。
- `name: str`
  - 频道名称。
- `tags: List[TagDetail]`
  - 该频道下所有可用标签。

`TagDetail` 定义见 `src/api/v1/schemas/meta/tag_detail.py`：

- `id: int`
  - 标签 Discord ID。
- `name: str`
  - 标签名称。

前端典型用途：

- 构建左侧频道导航列表。
- 渲染某一频道下的可用标签供筛选使用。

## 4. 用户偏好接口 `/v1/preferences`

路由定义见 `src/api/v1/routers/preferences.py`：

- `GET /v1/preferences/users/{user_id}`
  - 获取指定用户的搜索偏好。
- `PUT /v1/preferences/users/{user_id}`
  - 创建或更新指定用户的搜索偏好（部分字段更新）。

响应体模型为 `UserPreferencesResponse`：

- 基本信息：
  - `user_id: int`：Discord 用户 ID。
- 频道偏好：
  - `preferred_channels: Optional[List[int]]`：偏好频道 ID 列表。
- 作者偏好：
  - `include_authors: Optional[List[int]]`：只看这些作者。
  - `exclude_authors: Optional[List[int]]`：屏蔽这些作者。
- 标签偏好：
  - `include_tags: Optional[List[str]]`：必须包含的标签名。
  - `exclude_tags: Optional[List[str]]`：必须排除的标签名。
- 关键词偏好：
  - `include_keywords: str`：默认空字符串，用逗号/斜杠组合 AND/OR。
  - `exclude_keywords: str`：要排除的关键词。
  - `exclude_keyword_exemption_markers: List[str]`：默认 `["禁", "🈲"]`。
- 显示偏好：
  - `preview_image_mode: str`：`"thumbnail" | "full" | "none"`。
  - `results_per_page: int`：每页显示结果数量。
- 排序偏好：
  - `sort_method: str`：同 SearchRequest 中的 `sort_method`。
  - `custom_base_sort: str`：自定义排序时的基础排序算法。
- 时间偏好：
  - `created_after / created_before: Optional[str]`。
  - `active_after / active_before: Optional[str]`。

这些偏好可以在前端用于：

- 初始化搜索页的默认筛选条件；
- 在设置页展示和编辑用户个性化配置。

## 5. 线程模型与前端可见字段

内部线程模型见 `src/shared/models/thread.py` 的 `Thread` 类。

部分字段仅用于内部审计或排序控制（如 `show_flag`、`not_found_count`、`latest_update_at` 等），不会直接暴露到前端。
真正暴露给前端的数据通过 `ThreadDetail` 进行筛选和序列化（见 2.2.1 小节）。

前端可以依赖的字段主要包括：

- 业务展示：`title`、`first_message_excerpt`、`thumbnail_url`、`tags`。
- 时间相关：`created_at`、`last_active_at`。
- 交互反馈：`reaction_count`、`reply_count`。
- 排序统计：`display_count`。

## 6. 生产环境 vs 本地开发环境的数据差异

- **生产环境**：
  - `/v1/search` 调用真实数据库与索引服务，使用 UCB1 等参数进行结果排序。
  - `/v1/meta/channels` 从 `CacheService` 获取已索引频道与真实标签。
  - `/v1/preferences` 读写真实用户偏好数据。
  - Banner 数据由 `BannerService` 从数据库中读取。
- **本地开发环境（MSW）**：
  - 前端通过 MSW 模拟上述接口，只保证字段结构与真实接口一致，数据是有限的 Mock。
  - 某些值（如频道 ID、标签名、统计数字）是静态示例，不代表生产环境真实分布。

前端在设计类型与交互时应以本文件描述的 **生产环境字段与语义** 为准，不应依赖 Mock 数据中的具体值。