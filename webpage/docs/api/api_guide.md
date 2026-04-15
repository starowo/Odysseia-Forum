# Odysseia Forum 后端 API 指南

本文档为前端开发者提供 Odysseia Forum 后端 API 集成的完整指南。

**基础 URL**: `/v1` (例如本地开发环境: `http://localhost:10810/v1`)

## 前端 API 封装与类型生成

前端的 API 调用基于 `axios` 进行了统一封装，详见 `src/shared/api/client.ts`：
- **baseURL**: 从环境变量 `VITE_API_URL` 读取，缺省为 `http://localhost:10810/v1`。
- **拦截器**: 统一处理 `Authorization: Bearer <token>` 的注入，并全局拦截 `401 Unauthorized` 错误。

项目中使用了 `openapi-typescript` 进行 API 类型的自动化维护：
- 运行 `npm run gen:api`，会自动从后端生成 `openapi.json`，并提取 TypeScript 类型写入 `src/shared/types/openapi.d.ts`。
- 我们应尽量复用该文件中生成的接口类型规范出入参。


## 认证 (`/auth`)

后端使用 Discord OAuth2 进行身份认证。

### 登录
- **端点**: `GET /auth/login`
- **描述**: 将用户重定向到 Discord OAuth2 授权页面
- **流程**:
    1. 前端将用户重定向到 `/auth/login`
    2. 后端重定向到 Discord
    3. 用户同意授权
    4. Discord 重定向回后端 `/auth/callback`
    5. 后端重定向到前端(通过 `FRONTEND_URL` 配置),URL hash 包含 token: `/#token=<JWT_TOKEN>`
    6. 前端从 hash 提取 token 并存储(如 `localStorage`)

### 登出
- **端点**: `GET /auth/logout`
- **描述**: 清除会话并重定向用户
- **注意**: 前端也应清除存储的 token

### 检查认证状态
- **端点**: `GET /auth/checkauth`
- **描述**: 验证当前会话并返回用户信息
- **请求头**: `Authorization: Bearer <TOKEN>`
- **响应**:
  ```json
  {
    "loggedIn": true,
    "user": {
      "id": "string",
      "username": "string",
      "global_name": "string",
      "avatar": "string",
      "discriminator": "string"
    },
    "unread_count": 0
  }
  ```

---

## 搜索与标签 (`/search`, `/meta`)

### 全局搜索
- **端点**: `POST /search/`
- **描述**: 根据关键词、标签和频道筛选搜索帖子。支持跨服务器搜索和虚拟标签逻辑。
- **请求体 (`SearchRequest`)**:
  ```json
  {
    "guild_id": "int (可选, Snowflake)",
    "channel_ids": ["string (可选)"],
    "include_tags": ["string (可选)"],
    "exclude_tags": ["string (可选)"],
    "tag_logic": "and (可选, 默认'and', 或 'or')",
    "keywords": "string (可选, 支持高级语法)",
    "exclude_keywords": "string (可选)",
    "author_name": "string (可选)",
    "include_authors": ["int (可选)"],
    "exclude_authors": ["int (可选)"],
    "created_after": "YYYY-MM-DD (可选)",
    "created_before": "YYYY-MM-DD (可选)",
    "sort_method": "comprehensive (可选)",
    "sort_order": "desc (可选)",
    "limit": 24,
    "exclude_thread_ids": ["int (可选)"],
    "search_by_collection": false
  }
  ```

**参数说明**:
- `tag_logic`: 决定标签的匹配逻辑，支持 `'and'` 和 `'or'`。
- `search_by_collection`: 如果为 `true`，则说明当前正在针对收藏列表/书单内容执行检索。

**核心逻辑变动**:
1.  **多服务器支持 (`guild_id`)**: 若不传则搜索所有已索引服务器；若传则锁定特定服务器。
2.  **频道映射与虚拟标签 (`virtual_tags`)**:
    - 如果请求中只包含**一个** `channel_id`，且该频道在后台配置了映射（Mappings），响应中将包含 `virtual_tags`。
    - **显示逻辑**: 搜索结果中的帖子若来自被映射的源频道，会携带 `virtual_tags` 标记。
    - **筛选逻辑**: 在 `include_tags` 中传入虚拟标签名，后端会自动将其转化为对多个源频道的并集搜索。
3.  **精确匹配**: `include_tags` 和 `exclude_tags` 会优先检查是否匹配虚拟标签。

- **响应 (`SearchResponse`)**:
  ```json
  {
    "total": 123,
    "results": [
      {
        "thread_id": "string",
        "guild_id": "string",
        "channel_id": "string",
        "title": "string",
        "tags": ["真实标签"],
        "virtual_tags": ["虚拟映射标签"],
        "collected_flag": false,
        "thumbnail_urls": ["url"]
      }
    ],
    "available_tags": ["虚拟标签1", "真实标签A", "..."],
    "virtual_tags": ["虚拟标签1", "..."],
    "unread_count": 0
  }
  ```

### 获取频道和标签
- **端点**: `GET /meta/channels`
- **描述**: 获取所有已索引的频道及其可用标签。
- **查询参数**:
  - `guild_id`: 按服务器 ID 过滤频道列表。
  - `channel_ids`: 获取特定频道的元数据。
- **响应**: `List[Channel]` 对象。

---

## 关注 (`/follows`)

管理用户关注的帖子。

### 获取关注列表
- **端点**: `GET /follows`
- **描述**: 返回用户关注的帖子列表
- **查询参数**: 
  - `limit`: 返回数量(默认10,最大10000)
  - `offset`: 偏移量(默认0)
- **响应**: 包含 `threads` 数组和 `total` 总数

### 关注帖子
- **端点**: `POST /follows/{thread_id}`
- **描述**: 关注指定帖子
- **响应**: `{"success": true, "message": "关注成功"}`

### 取消关注
- **端点**: `DELETE /follows/{thread_id}`
- **描述**: 取消关注指定帖子

### 获取未读数量
- **端点**: `GET /follows/unread-count`
- **描述**: 返回未读关注帖子数量
- **响应**: `{"unread_count": 0}`

### 标记全部已读
- **端点**: `POST /follows/mark-viewed`
- **描述**: 将所有关注的帖子标记为已读

---

## Banner 申请 (`/banner`)

管理帖子轮播图申请。

### 申请 Banner
- **端点**: `POST /banner/apply`
- **描述**: 为帖子提交轮播图申请
- **权限**: 用户必须是帖子作者
- **请求体**:
  ```json
  {
    "thread_id": "string (纯数字)",
    "cover_image_url": "string (有效URL)",
    "target_scope": "string ('global' 或 channel_id)"
  }
  ```
- **响应**:
  ```json
  {
    "success": true,
    "message": "申请已提交",
    "application_id": 123
  }
  ```

### 获取活跃 Banner
- **端点**: `GET /banner/active`
- **查询参数**: `channel_id` (可选)
- **描述**: 返回当前活跃的轮播图列表

---

## 收藏与书单 (`/collection`, `/booklist`)

### 收藏系统 (`/collection`)

支持收藏帖子和书单。

#### 批量添加收藏
- **端点**: `POST /collection/batch/add`
- **请求体**:
  ```json
  {
    "target_ids": [123, 456],
    "target_type": 1
  }
  ```
  - `target_type`: 1=帖子 (THREAD), 2=书单 (BOOKLIST)

#### 批量移除收藏
- **端点**: `POST /collection/batch/remove`
- **请求体**: 同上

### 书单系统 (`/booklist`)

#### 创建书单
- **端点**: `POST /booklist/save`
- **请求体**:
  ```json
  {
    "title": "我的推荐",
    "description": "简介",
    "is_public": true,
    "display_type": 1
  }
  ```
  - `display_type`: 1=按加入时间倒序, 2=自定义排序

#### 搜索公开书单
- **端点**: `GET /booklist/list/page`
- **参数**: 
  - `keywords`: 标题/简介模糊搜索
  - `owner_id`: 按作者筛选
  - `sort_method`: 1-帖子数, 2-浏览数, 3-收藏数, 4-创建时间, 5-更新时间

#### 获取我的书单
- **端点**: `GET /booklist/my/list/page`
- **参数**:
  - `create_by_current_user`: true=我创建的
  - `collect_by_current_user`: true=我收藏的

#### 书单详情与管理
- `GET /booklist/detail/{id}`: 获取详情
- `PUT /booklist/update/{id}`: 更新元数据
- `DELETE /booklist/delete/{id}`: 删除书单

#### 书单内容管理
- `GET /booklist/item/list/page/{booklist_id}`: 获取书单内的帖子列表
- `POST /booklist/item/add/{booklist_id}`: 批量添加帖子
- `DELETE /booklist/item/delete/{booklist_id}`: 批量移除帖子
- `PATCH /booklist/item/update/{booklist_id}/{thread_id}`: 更新推荐语/排序

---

## 图片刷新 (`/fetch-images`)

从 Discord 刷新帖子缩略图。

### 批量刷新
- **端点**: `POST /fetch-images/`
- **描述**: 手动触发刷新,从 Discord 帖子首条消息获取最新图片
- **请求体**:
  ```json
  {
    "items": [
      {
        "thread_id": 123456789,
        "channel_id": 123
      }
    ]
  }
  ```
- **响应**:
  ```json
  {
    "results": [
      {
        "thread_id": "string",
        "thumbnail_urls": ["string"],
        "updated": true,
        "error": null
      }
    ]
  }
  ```

---

## 用户偏好设置 (`/preferences`)

管理用户特定设置。

### 获取偏好设置
- **端点**: `GET /preferences/users/{user_id}`
- **描述**: 获取用户的搜索偏好设置

### 更新偏好设置
- **端点**: `PUT /preferences/users/{user_id}`
- **描述**: 更新搜索偏好设置
- **请求体**: `UserPreferencesUpdateRequest` (根据后端实现,schema 可能有所不同)

---

## 高级搜索语法

前端支持以下高级语法(在后端 `KeywordParser` 中解析):

- **作者搜索**: `author:用户名` 或 `$author:用户名$`
- **标签搜索**: `$tag:标签名$`
- **精确匹配**: 用引号包围关键词 `"精确词组"`
- **排除关键词**: `-不想要的词` 或 `!排除词`

示例: `author:alice $tag:攻略$ -过期` 会搜索 alice 发布的带"攻略"标签且不包含"过期"的帖子。

---

## 类型说明

### Discord Snowflake IDs

Discord 使用 64 位整数 ID (Snowflake),在 JavaScript 中会超出 `Number.MAX_SAFE_INTEGER`,导致精度损失。

**解决方案**:
- 前端: 将 ID 存储和传输为**字符串**
- 后端: 
  - 序列化时转为字符串(`field_serializer`) 
  - 反序列化时从字符串转为整数进行查询

示例:
```typescript
// ✅ 正确
const channelId: string = "1393246224072839168";

// ❌ 错误 - 会丢失精度
const channelId: number = 1393246224072839168;
```

---

## 错误处理

所有端点遵循统一的错误响应格式:

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码:
- `200`: 成功
- `201`: 创建成功
- `204`: 成功但无内容返回
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误
- `503`: 服务不可用

---

## 开发建议

1. **认证**: 始终在请求头中携带 `Authorization: Bearer <TOKEN>`
2. **ID 处理**: 使用字符串存储和传输所有 Discord IDs
3. **分页**: 使用 `exclude_thread_ids` 而非 `offset` 实现无缝滚动
4. **缓存**: 合理设置 `staleTime` 避免过度请求
5. **错误处理**: 捕获 401 状态码并重定向到登录页
