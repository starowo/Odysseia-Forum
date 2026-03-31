# 项目结构说明 (V2 架构)

本项目现已升级为基于 **Feature-Sliced Design (FSD)** 改良的模块化架构，旨在解决“页面巨石化”与“状态边界模糊”等技术债。

## 📁 完整目录结构

```
Odysseia-Forum-Main/
├── webpage/                         # [开发] React 前端专区
│   ├── src/
│   │   ├── app/                    # [App 层] 全局配置、路由与 App 入口
│   │   │   ├── providers/          # 错误边界、路由守卫
│   │   │   ├── themes/             # ThemeContext 提供者
│   │   │   ├── App.tsx             # 应用主入口
│   │   │   └── router.tsx          # 路由定义
│   │   │
│   │   ├── pages/                  # [Pages 层] 完整的业务页面
│   │   │   ├── SearchPage/         # 搜索主页
│   │   │   ├── FollowsPage/        # 关注列表页
│   │   │   └── ...
│   │   │
│   │   ├── widgets/                # [Widgets 层] 高级组合组件
│   │   │   ├── thread-preview/     # 帖子预览浮层 (ThreadPreviewOverlay)
│   │   │   ├── layout/             # TopBar, AppSidebar, MainLayout
│   │   │   └── sidebar/            # ResizableSidebar
│   │   │
│   │   ├── features/               # [Features 层] 独立业务功能 (Store + API)
│   │   │   ├── search/             # 搜索核心
│   │   │   │   ├── hooks/          # useSearchParams (URL 参数协议层)
│   │   │   │   ├── store/          # searchStore (Banner UI), previewStore (帖子预览)
│   │   │   │   └── api/            # searchApi
│   │   │   ├── threads/            # 帖子动作 (useThreadActions)
│   │   │   ├── mascot/             # 吉祥物系统 (mascotStore)
│   │   │   └── notifications/      # 通知中心 (NotificationCenter)
│   │   │
│   │   ├── entities/               # [Entities 层] 核心领域模型与展示
│   │   │   ├── thread/             # 帖子实体 (ThreadCard, ThreadListItem, types)
│   │   │   ├── user/               # 用户实体 (AuthorAvatar)
│   │   │   └── channel/            # 频道实体
│   │   │
│   │   ├── shared/                 # [Shared 层] 通用底层逻辑
│   │   │   ├── ui/                 # 原子组件 (Button, LazyImage, Tooltip)
│   │   │   ├── lib/                # 纯函数库 (Utils, Tokenizer)
│   │   │   ├── hooks/              # 通用组件 Hooks (useTheme, useSettings)
│   │   │   ├── api/                # 基础 API Client (apiClient)
│   │   │   ├── styles/             # 全局样式与主题变量 (globals.css)
│   │   │   └── types/              # 通用类型定义 (openapi.d.ts)
│   │   │
│   │   ├── assets/                 # 图片、Banner、字体
│   │   └── main.tsx                # 应用渲染起点 (DOM Mount)
│   │
│   ├── tsconfig.json               # 别名映射 (@ -> src, @shared-types -> src/shared/types)
│   └── vite.config.ts              # 代理与构建配置
```

## 🎯 核心架构解析

### 1. 分层原则 (Layering)
- **Shared**: 基础中的基础，没有任何业务逻辑，可在任何地方引用。
- **Entities**: 纯粹的展示，描述“一个帖子长什么样”，不关心它在哪个页面出现。
- **Features**: 描述“一件事情怎么做”，通常包含 API 请求和状态管理。
- **Widgets**: 描述“一个区域怎么交互”，组合多个实体和功能，通常很大。
- **Pages**: 描述“一个航站楼”，只负责拼装 Widget，不写具体逻辑。

### 2. 关键 Feature 说明
- **Search (搜索)**:
  - **URL 参数协议**: `useSearchURLParams` 将搜索条件以 URL 为唯一数据来源。
  - **searchStore**: 精简后只保留 Banner UI 状态。
  - **previewStore**: 独立管理帖子预览状态。
- **Threads (交互)**: `ThreadActions` 包含点赞、转发等业务动作。
- **Mascot (吉祥物)**: 独立的交互逻辑，通过全局 Store 触发表情反馈。

### 3. 组件分层映射
- **Entities**: `ThreadCard`, `AuthorAvatar`, `ThreadStatusBadges`。
- **Widgets**: `GlobalThreadPreview`, `TopBar`, `AppSidebar`。
- **Shared UI**: `RippleButton`, `LazyImage`, `Tooltip`, `MarkdownText`。

## 📝 别名引用规范 (Paths)

为了代码整洁，我们配置了以下路径别名：
- **`@/*`**: 指向 `src/*`
- **`@shared-types/*`**: 指向 `src/shared/types/*` (主要用于 OpenAPI 生成的后端类型)

**推荐用法：**
```typescript
import { Thread } from '@/entities/thread/types';
import { LazyImage } from '@/shared/ui/LazyImage';
import { paths } from '@shared-types/openapi'; // 自动生成的后端协议类型
```

## 🛠 开发流程规范

1. **新增工具函数**: 放在 `shared/lib` 或 `features/[feature]/lib`。
2. **新增业务卡片**: 放在 `entities/[entity]`。
3. **新增业务逻辑**: 放在 `features/[feature]`。
4. **生成后端类型**: 运行 `npm run gen:api`。

## 📊 状态管理规范

| 状态类型 | 存放位置 | 示例 |
|---|---|---|
| 搜索条件 | URL searchParams | `?q=关键词&channel=xxx&sort=relevance` |
| 服务端数据 | React Query 缓存 | 搜索结果、频道列表、用户信息 |
| 帖子预览 | `previewStore` (Zustand) | 当前预览的 Thread 对象 |
| Banner UI | `searchStore` (Zustand) | Banner 可见性、轮播数据 |
| 用户偏好 | localStorage + `useSettings` | 主题、字体大小、布局模式 |
