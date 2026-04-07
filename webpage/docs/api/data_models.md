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

- `guild_id: Optional[int]`
  - 要搜索的服务器 ID，为空则不按服务器过滤。
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
- `exclude_thread_ids: Optional[List[int]]`
  - 已在前端展示的帖子 ID 列表，用于去重或无缝滚动。
- `search_by_collection: Optional[bool]`
  - 是否仅搜索当前用户已收藏的帖子。
- `offset: int`
  - 偏移量，从 0 开始。

> 生产环境中，`search.py` 还会通过 `KeywordParser` 对 `keywords` 做二次解析，抽取作者名、精确关键词与排除词，组合成实际用于检索的 `final_keywords` 和 `final_exclude_keywords`。

### 2.2 前端参数装配机制 (Tokenization & Mapping)
虽然最终的网络传输体符合 `SearchRequest` 模型，但前端在组装数据时引入了**全局中间态分词层 (`src/shared/lib/searchTokenizer.ts`)**：
- 前端界面的源字符串 `query`（如 `"关键词 $tag:音乐$ -$author:张三$"`）会被解析出不同的 Token。
- `searchApi.ts` 会将打散的 Token 字段拼装到请求体中：
  - `$tag:` 提取后追加到 `include_tags`。
  - `-$tag:` 提取后追加到 `exclude_tags`。
  - `$author:` 提取后转换为 `author:"姓名"` 字符串追加到 `keywords` 字段供后端的 `KeywordParser` 进一步解析，而不会直接使用 `SearchRequest.author_name` 字段。
  - `$channel:` 优先合并到 `channel_ids` 列表。

### 2.3 SearchResponse 响应字段

定义见 `src/api/v1/schemas/search/search_response.py`。该响应继承自 `PaginatedResponse[ThreadDetail]`，并增加了若干额外字段。

基础分页字段：

- `total: int`
- `limit: int`
- `offset: int`

#### 2.2.1 ThreadDetail 帖子字段

`ThreadDetail` 是搜索结果中单个帖子的公开视图，其字段主要来自 `src/shared/models/thread.py`：

- `thread_id: str`
  - 帖子的 Discord ID（以字符串形式返回）。
- `guild_id: str`
  - 帖子所属服务器的 Discord ID（字符串）。
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
  - 帖子关联的真实 Discord 标签名称列表。
- `virtual_tags: List[str]`
  - 帖子关联的**虚拟映射标签**名称列表。当帖子来自被映射的源频道时呈现。
- `collected_flag: bool`
  - 当前用户是否已关注/收藏该帖子。

#### 2.2.2 扩展字段

除了 `results: List[ThreadDetail]` 外，`SearchResponse` 还包含：

- `available_tags: List[str]`
  - 搜索结果关联的可用标签名列表。
  - **排序逻辑**: 虚拟标签（来自 Mappings）置顶，随后是各频道的真实标签（去重）。
- `virtual_tags: List[str]`
  - 当前选定频道下定义的所有可用虚拟映射标签。
- `banner_carousel: List[BannerItem]`
  - 当前频道以及全局可展示的 Banner 列表，最多 8 个。
  - `BannerItem` 字段：
    - `thread_id: str`
    - `title: str`
    - `cover_image_url: str`
    - `channel_id: str`
- `unread_count: int`
  - 当前用户关注列表中的未读更新数量（由 `FollowService.get_unread_count` 统计）。

### 2.4 核心机制：频道映射 (Channel Mappings)

当后端 `config.json` 中配置了 `channel_mappings` 时，API 会产生以下行为：

1. **虚拟标签生成**: 如果搜索请求中指定了某个作为“目标”的 `channel_id`，后端会读取映射配置，将对应的源频道汇总到该目标频道名下，并生成 `virtual_tags`。
2. **请求转换**: 前端在 `include_tags` 中传入虚拟标签名时，后端会自动将请求扩展为包含所有对应 `source_channel_ids` 的大范围搜索。
3. **标签透传**: 搜索结果中的 `ThreadDetail.virtual_tags` 会标注该贴属于哪个虚拟分类，方便前端展示（例如在帖子卡片上高亮显示映射标签）。

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
  - `/v1/follows` 及 `/v1/follows/unread-count` 提供关注列表与未读更新数量。
  - `/v1/auth/checkauth` 在返回登录状态时也附带未读更新数量。
- **本地开发环境（MSW）**：
  - 前端通过 MSW 模拟上述接口，只保证字段结构与真实接口一致，数据是有限的 Mock。
  - 某些值（如频道 ID、标签名、统计数字）是静态示例，不代表生产环境真实分布。

前端在设计类型与交互时应以本文件描述的 **生产环境字段与语义** 为准，不应依赖 Mock 数据中的具体值。

---

## 7. 关注列表与“有更新”相关数据

这一节补充说明和 **关注 / 更新状态** 相关、但在搜索结果里不一定直接出现的字段，方便前端在设计交互时统一参考。

### 7.1 关注列表 `/v1/follows/`

路由定义见 [`src/api/v1/routers/follows.py`](src/api/v1/routers/follows.py:15)，依赖 `get_current_user`：

- 方法：`GET /v1/follows/`
- 查询参数：
  - `limit: int = 10000`
  - `offset: int = 0`
- 响应结构（非 Pydantic，手动构造的 JSON）：

```jsonc
{
  "total": 123,
  "threads": [
    {
      "thread_id": "1234567890",
      "channel_id": "987654321",
      "title": "帖子标题",
      "author_id": "1122334455",
      "created_at": "2024-01-01T12:00:00+00:00",
      "last_active_at": "2024-01-02T12:00:00+00:00",
      "latest_update_at": "2024-01-02T12:30:00+00:00",
      "latest_update_link": "https://discord.com/...",
      "reaction_count": 10,
      "reply_count": 5,
      "first_message_excerpt": "首条消息摘要……",
      "thumbnail_url": "https://...",
      "tags": ["标签A", "标签B"],
      "followed_at": "2024-01-01T12:00:00+00:00",
      "last_viewed_at": "2024-01-02T12:00:00+00:00",
      "has_update": true
    }
  ],
  "limit": 10000,
  "offset": 0
}
```

字段来源见 [`FollowService.get_user_follows`](src/ThreadManager/services/follow_service.py:227)：

- 线程字段（来自 `Thread` 模型）：
  - `thread_id: str`
  - `channel_id: str`
  - `title: str`
  - `author_id: str`
  - `created_at: datetime`
  - `last_active_at: Optional[datetime]`
  - `latest_update_at: Optional[datetime]`
  - `latest_update_link: Optional[str]`
  - `reaction_count: int`
  - `reply_count: int`
  - `first_message_excerpt: Optional[str]`
  - `thumbnail_url: Optional[str]`
  - `tags: List[str]`（从 `thread.tags` 映射而来）
- 关注关系字段（来自 `ThreadFollow`）：
  - `followed_at: datetime`
  - `last_viewed_at: Optional[datetime]`
  - `has_update: bool`
    - 逻辑：`thread.latest_update_at` 存在且晚于 `last_viewed_at`，或者 `last_viewed_at` 为 `null` 时视为 `true`。

前端典型用途（设计指引）：

- **关注页卡片**：
  - 使用 `has_update` 在卡片上加红点 / “有更新”标记。
  - 使用 `latest_update_at` / `latest_update_link` 定位到最新回复（如果需要）。
- **搜索结果页**：
  - 当前的搜索结果 `ThreadDetail` **不包含** `has_update`/`followed_at` 等字段，因此:
    - 搜索结果中无法直接知道某贴是否已关注或是否有未读更新；
    - 若希望在搜索结果中显示“已关注/有更新”状态，需要后端扩展 `ThreadDetail` 或提供额外接口。

### 7.2 未读更新数量 `unread_count`

未读更新有三处来源，语义一致：

1. 搜索接口 [`/v1/search`](src/api/v1/routers/search.py:189)：
   - 返回的 [`SearchResponse`](src/api/v1/schemas/search/search_response.py:36) 中包含：

     ```py
     unread_count: int = Field(
         default=0,
         description="当前用户关注列表的未读更新数量"
     )
     ```

   - 值来自 `FollowService.get_unread_count(user_id)`。

2. 认证检查接口 [`/v1/auth/checkauth`](src/api/v1/routers/auth.py:198)：
   - 返回 JSON 中同样包含 `unread_count` 字段：

     ```jsonc
     {
       "loggedIn": true,
       "user": { ... },
       "unread_count": 3
     }
     ```

   - 便于前端在全局导航（如登录后立刻）显示未读徽标。

3. 关注路由 [`/v1/follows/unread-count`](src/api/v1/routers/follows.py:100)：
   - 方法：`GET /v1/follows/unread-count`
   - 响应：`{"unread_count": number}`

前端可以根据实际需求选择数据来源：

- **全局侧边栏徽标**：优先使用 `/auth/checkauth` 或 `/follows/unread-count`。
- **搜索页头部统计**：直接使用 `SearchResponse.unread_count`，保持一次请求拿齐结果与未读数。

### 7.3 当前文档 vs 前端使用情况说明

- 本文件现在覆盖的内容：
  - 搜索接口 `/v1/search`：`SearchRequest`、`SearchResponse`、`ThreadDetail` 的所有字段；
  - 元数据 `/v1/meta/channels`：频道和标签结构；
  - 用户偏好 `/v1/preferences/users/{user_id}`：全部字段；
  - 关注列表 `/v1/follows/`：帖子 + 关注关系字段（含 `has_update` 等）；
  - 未读更新数量：`/v1/search`、`/v1/auth/checkauth`、`/v1/follows/unread-count` 中的 `unread_count`。

- 前端已经使用的字段（截至当前实现）：
  - 搜索结果卡片/列表：
    - `title`、`first_message_excerpt`、`thumbnail_url`、`tags`、
      `created_at`、`reaction_count`、`reply_count`。
  - 搜索页统计与筛选：
    - `total`、`limit`、`offset`、`available_tags`、`banner_carousel`。
  - 关注页：
    - 关注列表接口的基础帖子字段（标题、摘要、封面、标签、计数等）。
  - 未读数：
    - 尚未在 UI 中展示，但可以从上述三个接口任一处接入。

- 目前尚未在 UI 中利用、但已经有的有用数据：
  - `has_update`：可用于关注页、未来的搜索结果中突出“有新内容”的帖子（红点/高亮）。
  - `latest_update_at` / `latest_update_link`：可用于“跳转到最新更新”按钮。
  - `display_count`：主要用于排序算法（UCB1），不建议直接展示，但可用于 debug / 实验性 UI。


## 8. 收藏与书单 (Collections & Booklists)

新增的收藏系统与书单系统，提供了更灵活的内容组织方式。

### 8.1 收藏类型 `CollectionType`

在 `/collection/batch/add` 等接口中使用 `target_type` 字段区分：

- `1`: **THREAD** (帖子)
- `2`: **BOOKLIST** (书单)

### 8.2 书单详情 `BooklistDetail`

书单列表与详情接口返回的核心模型 `src/api/v1/schemas/booklist/booklist_detail.py`：

- `id: int`: 书单 ID
- `title: str`: 标题
- `description: Optional[str]`: 简介
- `cover_image_url: Optional[str]`: 封面
- `owner_id: str`: 创建者用户 ID (字符串)
- `is_public: bool`: 是否公开
- `display_type: int`: 排序方式 (1=加入时间倒序, 2=自定义排序)
- `item_count: int`: 包含帖子数
- `collection_count: int`: 被收藏数
- `view_count: int`: 浏览器
- `collected_flag: bool`: **(动态)** 当前用户是否已收藏该书单

### 8.3 书单项 `BooklistItemDetail`

书单内容接口 `/booklist/item/list/page/{id}` 返回的列表项 `src/api/v1/schemas/booklist/booklist_item_detail.py`：

- `booklist_item_id: int`: 关联记录 ID
- `thread_id: str`: 帖子 ID
- `title, author, thumbnail_urls...`: 帖子的基础快照信息
- `comment: Optional[str]`: **推荐语/书单主备注**
- `display_order: int`: 排序权重
- `collected_flag: bool`: **(动态)** 当前用户是否收藏了该帖子