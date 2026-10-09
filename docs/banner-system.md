# Banner 系统说明

Banner 系统是一个**「申请 → 审核 → 轮播展示」**的完整工作流，服务于 Discord 论坛。它允许用户为自己的帖子申请展示 Banner，审核员审批后，Banner 会进入轮播队列，按时间自动轮替。

---

## 1. 整体架构

```
┌───────────────┐     ┌───────────────┐      ┌─────────────┐
│  FastAPI 接口 │───▶│  BannerService │────▶│   数据库    │
│  (REST API)   │     │  (业务逻辑)    │      │  (3 张表)   │
└───────────────┘     └───────────────┘      └─────────────┘
                            ▲
┌──────────────┐            │
│  Discord Bot │────────────┘
│  (用户交互)   │
└──────────────┘
```

系统由三层组成：
- **FastAPI** — 提供 REST API，处理外部请求（Banner 申请提交、获取活跃 Banner）
- **Discord Bot** — 提供用户交互界面（申请按钮、表单、审核按钮）
- **BannerService** — 核心业务逻辑层，封装所有数据库操作

---

## 2. 数据库模型（3 张表）

### `banner_application` — 申请表

记录每一次 Banner 申请及其审核状态。

### `banner_carousel` — 轮播表

记录当前正在展示的 Banner（已批准且未过期）。

### `banner_waitlist` — 等待队列表

当轮播已满时，新批准的 Banner 会排入此队列，等待轮播有空位后被自动晋升。

---

## 3. API 端点

REST API 位于 [src/api/v1/routers/banner.py](../src/api/v1/routers/banner.py)，前缀 `/v1/banner`，全部需要认证。

### `POST /v1/banner/apply` — 提交 Banner 申请

### `GET /v1/banner/active` — 获取活跃 Banner

**查询参数：**

- `channel_ids`（可选，可重复传入）：频道 ID 列表，例如 `?channel_ids=123&channel_ids=456`
- `channel_id`（可选）：兼容旧调用的单个频道 ID；与 `channel_ids` 同时传入时会合并去重

范围优先级为：显式频道参数 → 用户偏好 `preferred_channels` → 全部频道。
显式参数覆盖偏好频道，不取交集；未传参数且偏好未设置、为空或读取失败时返回全部频道。
指定频道或使用偏好时按其列表顺序去重选择候选范围；全部模式包含未配置但仍有轮播的频道。
每个范围先按轮播位置、记录 ID 选择候选，再将全局与频道候选统一按轮播记录 ID 升序返回；
频道参数顺序不影响最终展示顺序。频道与全局 Banner 容量均为 **3 个**。
仅返回未过期轮播，不读取等待列表或历史申请。

帖子型 Banner 会自动应用当前用户的反选偏好：排除作者、真实/虚拟 TAG、
排除关键词及关键词豁免标记。频道型 Banner 的展示标题同样应用反选关键词及豁免规则，
复用搜索分词、前缀匹配和大小写处理，但不应用作者或标签反选。
全局 Banner 同样参与反选；正选作者、标签、关键词和时间偏好不限制结果。
过滤后仍保持原轮播顺序，不从等待列表补位。偏好读取失败时跳过偏好过滤，
但仍检查帖子公开状态；过滤查询失败返回接口错误。

---

## 4. Discord Bot 组件

### Cog：`BannerManagement`

位于 [src/banner/cog.py](../src/banner/cog.py)，提供：

| 功能 | 说明 |
|------|------|
| `/banner 创建申请通道` | 向当前频道发送申请入口按钮（管理员/机器人管理员权限） |
| `/banner 查看状态` | 查看当前轮播统计信息（管理员/机器人管理员权限） |
| `cleanup_expired_banners()` | 定时任务，**每小时**自动清理过期 Banner 并从等待队列晋升 |

在 `cog_load()` 时注册持久化视图（`BannerApplicationButtonView`、`ReviewView`），确保 Bot 重启后按钮仍然可用。

### 用户交互流程（Discord Views）

```
用户点击 "申请Banner展示" 按钮
  └─ BannerApplicationButtonView  ── 检查用户角色权限
       └─ ApplicationFormModal     ── 填写 帖子ID + 封面URL
            └─ ChannelSelectionView ── 选择展示范围（全局/某频道）
                 └─ BannerService.validate_and_create_application()
                      └─ send_review_message() 推送审核消息到审核频道
```

### 审核交互流程

```
审核员点击 "批准"
  └─ BannerService.approve_application()
       ├─ 轮播未满 → 写入 banner_carousel（start=now, end=now+3天）
       └─ 轮播已满 → 写入 banner_waitlist（排队等待）
  └─ DM 通知申请人 "你的 Banner 已通过审核"
  └─ 归档到 archive_thread

审核员点击 "拒绝"
  └─ RejectReasonModal ── 填写拒绝理由
  └─ BannerService.reject_application()
  └─ DM 通知申请人
  └─ 归档到 archive_thread
```

**相关文件：**
| 文件 | 功能 |
|------|------|
| [src/banner/views/banner_application_button_view.py](../src/banner/views/banner_application_button_view.py) | 申请入口按钮 |
| [src/banner/views/application_form_modal.py](../src/banner/views/application_form_modal.py) | 申请表单模态框 |
| [src/banner/views/channel_selection_view.py](../src/banner/views/channel_selection_view.py) | 频道选择下拉菜单 |
| [src/banner/views/review_view.py](../src/banner/views/review_view.py) | 审核批准/拒绝按钮 + 拒绝理由模态框 |

---

## 5. 业务逻辑服务

核心类 `BannerService` 位于 [src/banner/banner_service.py](../src/banner/banner_service.py)。

### 关键常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `GLOBAL_MAX_BANNERS` | 3 | 全局 Banner 最多同时展示数 |
| `CHANNEL_MAX_BANNERS` | 3 | 每个频道 Banner 最多同时展示数 |
| `BANNER_DURATION_DAYS` | 3 | 每个 Banner 展示天数 |

---

## 6. 完整数据流

```
┌──────────────────────────────────────────────────────────────┐
│                        申请阶段                               │
├──────────────────────────────────────────────────────────────┤
│  用户 → 点击按钮 → 填写表单 → 选择频道                        │
│       → BannerService.validate_and_create_application()       │
│       → 写入 banner_application (status=pending)              │
│       → Redis 队列 → Bot 发送审核消息到审核频道                 │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                        审核阶段                               │
├──────────────────────────────────────────────────────────────┤
│  审核员 → 点击 批准/拒绝 → ReviewView                         │
│                                                              │
│  【批准】 approve_application()                               │
│     ├─ 轮播未满 → 写入 banner_carousel (start=now, end=+3天)  │
│     └─ 轮播已满 → 写入 banner_waitlist (排队等待)              │
│                                                              │
│  【拒绝】 reject_application()                                │
│     └─ 记录理由 + 审核人                                      │
│                                                              │
│  → DM 通知申请人 → 归档到 archive_thread                     │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                        展示阶段                               │
├──────────────────────────────────────────────────────────────┤
│  GET /v1/banner/active → BannerService.get_active_banners()  │
│     → 查询 banner_carousel WHERE end_time > now               │
│     → 各范围选取候选后，统一按轮播记录 ID 升序返回              │
│       （全局与频道容量均为 3）                                 │
│     → 帖子型 Banner 应用当前用户反选偏好                       │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                   维护阶段（每小时自动）                        │
├──────────────────────────────────────────────────────────────┤
│  BannerService.cleanup_expired_banners()                      │
│     → 删除过期的 banner_carousel 行                           │
│     → 从 banner_waitlist 按 FIFO 晋升到 banner_carousel       │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. 配置

在 `config.json` 中的 `banner` 段：

```json
{
  "banner": {
    "enabled": true,
    "applicant_role_ids": "role_id_1,role_id_2",
    "reviewer_role_ids": "role_id_1,role_id_2,role_id_3",
    "review_thread_id": 1234567890123456789,
    "archive_thread_id": 9876543210987654321,
    "available_channels": {
      "1374474903981527082": "频道A",
      "1374481342825238821": "频道B"
    }
  }
}
```

| 配置项 | 说明 |
|------|------|
| `enabled` | 是否启用 Banner 系统 |
| `applicant_role_ids` | 允许申请 Banner 的 Discord 角色 ID（逗号分隔） |
| `reviewer_role_ids` | 允许审核 Banner 的 Discord 角色 ID（逗号分隔） |
| `review_thread_id` | 审核消息发送到哪个 Discord 帖子 |
| `archive_thread_id` | 审核记录归档到哪个 Discord 帖子 |
| `available_channels` | 可供用户选择的展示频道（key 为频道 ID，value 为显示名称） |

配置模板见 [config.example.json](../config.example.json)。

---

## 8. 设计要点

### 容量控制
- **全局最多 3 个** Banner 同时展示
- **每个频道最多 3 个** Banner 同时展示
- 超额申请进入 `banner_waitlist` 等待队列

### 时间管理
- 每个 Banner 展示 **3 天** 后自动过期
- 每小时定时任务清理过期项并晋升等待队列中的下一个

### 数据隔离
- Banner 分为**全局**（`target_scope = "global"`，`channel_id = NULL`）和**频道专属**两种
- 获取时合并两类 Banner（专属 + 全局），分属不同容量上限

### 持久化视图
- 所有 Discord UI 组件使用持久化视图（`custom_id`），Bot 重启后按钮仍可响应

### 自动降级
- 搜索接口获取 Banner 失败时返回空列表 `[]`，不影响搜索结果

---

## 9. 文件索引

| 文件 | 角色 |
|------|------|
| [src/api/v1/routers/banner.py](../src/api/v1/routers/banner.py) | REST API 端点（申请提交、获取活跃 Banner） |
| [src/banner/banner_service.py](../src/banner/banner_service.py) | 核心业务逻辑 + `send_review_message()` |
| [src/models/banner_application.py](../src/models/banner_application.py) | 申请表模型 `banner_application` |
| [src/models/banner_carousel.py](../src/models/banner_carousel.py) | 轮播表模型 `banner_carousel` |
| [src/models/banner_waitlist.py](../src/models/banner_waitlist.py) | 等待队列表模型 `banner_waitlist` |
| [src/banner/cog.py](../src/banner/cog.py) | Discord Bot 命令与定时清理任务 |
| [src/banner/views/banner_application_button_view.py](../src/banner/views/banner_application_button_view.py) | 申请入口按钮视图 |
| [src/banner/views/application_form_modal.py](../src/banner/views/application_form_modal.py) | 申请表单模态框 |
| [src/banner/views/channel_selection_view.py](../src/banner/views/channel_selection_view.py) | 频道选择下拉菜单 |
| [src/banner/views/review_view.py](../src/banner/views/review_view.py) | 审核批准/拒绝按钮 + 拒绝理由模态框 |
| [src/api/v1/schemas/banner/banner_item.py](../src/api/v1/schemas/banner/banner_item.py) | API 响应 Schema `BannerItem` |
| [src/api/v1/schemas/banner/__init__.py](../src/api/v1/schemas/banner/__init__.py) | Schema 包导出 |
| [src/api/v1/schemas/search/search_response.py](../src/api/v1/schemas/search/search_response.py) | 搜索响应中的 `banner_carousel` 字段 |
| [src/shared/enum/application_status.py](../src/shared/enum/application_status.py) | `ApplicationStatus` 枚举（pending/approved/rejected） |
| [src/models/__init__.py](../src/models/__init__.py) | 模型导出 |
