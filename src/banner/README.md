# 🎨 Banner 模块

## 📖 简介
`banner` 模块实现了论坛首页的 **Banner 轮播推荐系统**。允许符合资格的用户申请将自己的帖子展示在轮播位中，经管理员审核后上线展示，到期自动下架并从候补队列中递补。

---

## 🏗️ 核心组件

### 1. `cog.py` — 模块入口
- 注册 `/banner` 命令组（创建申请通道、查看状态）。
- 启动每小时执行的过期清理定时任务 (`cleanup_expired_banners`)。
- 注册持久化视图（申请按钮、审核按钮），确保 Bot 重启后仍可响应交互。

### 2. `banner_service.py` — 核心业务服务
封装 Banner 系统的全部业务逻辑：
- **申请流程**: 校验用户资格、帖子有效性、频道限额，创建申请记录。
- **审核流程**: 通过/拒绝申请，通过后自动加入轮播或候补队列。
- **轮播管理**: 维护当前展示列表，全频道与频道候选统一按轮播记录 ID 升序展示；全频道最多 3 个，单频道容量为 3 个。
- **候补队列**: 超出限额的申请进入等待列表，到期清理后自动递补上线。
- **过期清理**: 检查并移除已到期的 Banner，触发候补递补。

### 3. `views/` — 交互视图
- `banner_application_button_view.py`: 申请按钮（持久化视图），用户点击后弹出频道选择。
- `channel_selection_view.py`: 频道选择下拉框，选择后弹出申请表单。
- `application_form_modal.py`: 申请表单模态框（填写帖子链接等信息）。
- `review_view.py`: 管理员审核面板（通过/拒绝按钮，持久化视图）。

---

## 📂 目录结构

```text
banner/
├── cog.py                              # 命令注册、定时任务、持久化视图加载。
├── banner_service.py                   # 申请/审核/轮播/候补/过期清理业务逻辑。
└── views/
    ├── banner_application_button_view.py  # 申请入口按钮（持久化）。
    ├── channel_selection_view.py          # 频道选择交互。
    ├── application_form_modal.py          # 申请表单模态框。
    └── review_view.py                     # 审核面板（持久化）。
```

---

## ⚙️ 配置项 (`config.json` → `banner`)

| 配置键 | 说明 |
|--------|------|
| `enabled` | 是否启用 Banner 系统 |
| `applicant_role_ids` | 允许申请的身份组 ID（逗号分隔） |
| `review_thread_id` | 审核消息发送的 Thread ID |
| `archive_thread_id` | 审核存档的 Forum 频道 ID |
| `available_channels` | 可选展示频道（`{频道ID: 频道名}` 字典） |
