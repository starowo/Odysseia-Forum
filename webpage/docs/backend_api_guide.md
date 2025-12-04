# Odysseia Forum 后端 API 指南

本文档为前端开发者提供 Odysseia Forum 后端 API 集成的完整指南。

**基础 URL**: `/v1` (例如本地开发环境: `http://localhost:10810/v1`)

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
- **描述**: 根据关键词、标签和频道筛选搜索帖子
- **请求体**:
  ```json
  {
    "keywords": "string (可选)",
    "channel_ids": ["string (可选)"],
    "include_tags": ["string (可选)"],
    "exclude_tags": ["string (可选)"],
    "tag_logic": "and (可选, 默认'and')",
    "author_name": "string (可选)",
    "created_after": "YYYY-MM-DD (可选)",
    "created_before": "YYYY-MM-DD (可选)",
    "sort_method": "comprehensive (可选)",
    "sort_order": "desc (可选)",
    "limit": 24,
    "offset": 0,
    "exclude_thread_ids": ["int (可选)"]
  }
  ```
- **响应**: `SearchResponse` 对象,包含帖子列表、总数、可用标签和轮播图

**重要说明**:
- `channel_ids`: 为避免 JavaScript 精度损失,应传递**字符串数组**(后端会转换为整数)
- `author_name`: 支持模糊匹配作者的全局用户名或昵称
- `exclude_thread_ids`: 已加载的帖子 ID 列表,用于无缝滚动加载

### 获取频道和标签
- **端点**: `GET /meta/channels`
- **描述**: 获取所有已索引的频道及其可用标签
- **响应**:
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "tags": [
        { "id": "string", "name": "string" }
      ]
    }
  ]
  ```
- **注意**: **没有**独立的 `/tags` 端点,标签与频道绑定

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
