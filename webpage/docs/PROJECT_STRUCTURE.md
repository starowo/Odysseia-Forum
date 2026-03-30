# 项目结构说明

## 📁 完整目录结构

```
NewWebpage/
├── public/                          # 静态资源
│   └── vite.svg
│
├── src/
│   ├── app/                         # 应用核心配置
│   │   ├── App.tsx                 # 根组件（Provider 配置，全局状态）
│   │   └── router.tsx              # 路由配置（定义页面路由规则）
│   │
│   ├── pages/                       # 页面组件（路由目标）
│   │   ├── AuthPage/               # 认证相关页面
│   │   │   ├── LoginPage.tsx      # 登录页
│   │   │   └── CallbackPage.tsx   # OAuth 回调处理页
│   │   │
│   │   ├── SearchPage/             # 搜索主页
│   │   │   └── index.tsx          # 搜索页面入口
│   │   │
│   │   ├── FollowsPage/            # 关注列表页面
│   │   ├── SettingsPage/           # 设置页面
│   │   ├── AboutPage/              # 关于页面
│   │   ├── TagsPage/               # 标签页面
│   │   ├── NotFoundPage/           # 404 页面
│   │   └── TestPage.tsx            # 测试页面
│   │
│   ├── features/                    # 业务功能模块（按领域划分）
│   │   ├── auth/                   # 认证功能
│   │   │   ├── api/               # 认证相关 API
│   │   │   └── hooks/             # 认证相关 Hooks
│   │   │
│   │   ├── threads/                # 帖子/串功能（核心业务）
│   │   │   ├── api/               # 帖子相关 API
│   │   │   └── components/        # 帖子相关组件
│   │   │       ├── ThreadCard.tsx         # 帖子卡片（列表展示）
│   │   │       ├── ThreadListItem.tsx     # 帖子列表项（紧凑视图）
│   │   │       ├── ThreadPreviewOverlay.tsx # 帖子预览弹窗
│   │   │       ├── ThreadActions.tsx      # 帖子操作栏
│   │   │       ├── MultiImageGrid.tsx     # 多图展示网格
│   │   │       ├── AuthorAvatar.tsx       # 作者头像
│   │   │       └── GlobalThreadPreview.tsx # 全局预览容器
│   │   │
│   │   ├── search/                 # 搜索功能
│   │   │   ├── api/               # 搜索相关 API
│   │   │   └── store/             # 搜索状态管理 (Zustand)
│   │   │
│   │   ├── banner/                 # 顶部 Banner 功能
│   │   ├── follows/                # 关注功能
│   │   ├── mascot/                 # 吉祥物/看板娘功能
│   │   │   ├── assets.ts          # 资源配置
│   │   │   ├── components/        # 类脑娘 UI 组件
│   │   │   │   └── MascotDialog.tsx
│   │   │   ├── config/            # 触发器与台词配置
│   │   │   └── store/             # 类脑娘状态管理
│   │   │
│   │   └── notifications/          # 通知功能
│   │
│   ├── components/                  # 通用/共享组件
│   │   ├── layout/                 # 布局组件
│   │   │   ├── RootLayout.tsx     # 根布局容器
│   │   │   ├── MainLayout.tsx     # 主内容区域布局
│   │   │   ├── AppSidebar.tsx     # 侧边栏导航
│   │   │   ├── TopBar.tsx         # 顶部导航栏
│   │   │   ├── FilterBar.tsx      # 筛选工具栏
│   │   │   ├── StatsBar.tsx       # 统计信息栏
│   │   │   ├── BannerCarousel.tsx # 首页轮播图
│   │   │   ├── UserCard.tsx       # 用户信息卡片
│   │   │   └── ThemeProvider.tsx  # 主题上下文提供者
│   │   │
│   │   ├── common/                 # 通用 UI 组件
│   │   │   ├── RippleButton.tsx   # 水波纹按钮
│   │   │   ├── LazyImage.tsx      # 懒加载图片
│   │   │   ├── MarkdownText.tsx   # Markdown 渲染组件
│   │   │   ├── HighlightText.tsx  # 高亮文本组件
│   │   │   ├── SearchTokenInput.tsx # 搜索 Token 输入框
│   │   │   ├── ScrollProgress.tsx # 滚动进度条
│   │   │   ├── ScrollToTop.tsx    # 回到顶部按钮
│   │   │   ├── Spoiler.tsx        # 防剧透遮罩
│   │   │   ├── ThemeToggle.tsx    # 主题切换按钮
│   │   │   └── Tooltip.tsx        # 工具提示
│   │   │
│   │   ├── icons/                  # 图标组件
│   │   │
│   │   ├── ErrorBoundary.tsx       # 错误边界
│   │   ├── ProtectedRoute.tsx      # 路由守卫组件
│   │   ├── ResizableSidebar.tsx    # 可调整大小侧边栏
│   │   ├── SearchHistory.tsx       # 搜索历史组件
│   │   └── SearchSuggestions.tsx   # 搜索建议组件
│   │
│   ├── hooks/                       # 全局 Hooks
│   │   └── (通用 Hooks)
│   │
│   ├── lib/                         # 工具库与配置
│   │   ├── api/                    # API 客户端配置
│   │   ├── utils/                  # 工具函数文件夹
│   │   ├── utils.ts                # 通用工具函数
│   │   ├── settings.ts             # 设置相关逻辑
│   │   ├── icons.ts                # 图标映射/配置
│   │   ├── searchHistory.ts        # 搜索历史逻辑
│   │   └── searchTokenizer.ts      # 搜索词法分析器
│   │
│   ├── styles/                      # 样式文件
│   │   ├── globals.css            # 全局 CSS 变量与样式
│   │   └── themes.ts              # 主题定义
│   │
│   ├── types/                       # TypeScript 类型定义
│   │
│   ├── assets/                      # 静态资源（图片、字体等）
│   │
│   └── main.tsx                     # 应用入口文件
│
├── .env.example                     # 环境变量示例
├── package.json                    # 项目依赖配置
├── tailwind.config.js             # Tailwind CSS 配置
├── tsconfig.json                  # TypeScript 配置
└── vite.config.ts                 # Vite 构建配置
```

## 🎯 核心架构解析

### 1. 模块化设计 (Features)
项目采用 **Feature-based** 架构，将业务逻辑内聚在 `src/features` 目录下。每个 Feature 包含其独有的：
- **components/**: 业务组件，仅在该功能内使用。
- **api/**: 相关的后端接口请求。
- **hooks/**: 业务逻辑封装。

**核心 Feature：Threads (帖子)**
- `ThreadCard`: 首页瀑布流展示的卡片组件。
- `ThreadPreviewOverlay`: 点击帖子后弹出的详情预览层，支持快速浏览。
- `ThreadActions`: 帖子的交互操作（点赞、回复、引用等）。

### 2. 组件分层 (Components)
- **Layout Components (`components/layout`)**: 负责页面的整体结构。
    - `AppSidebar`: 左侧导航，包含服务器列表和用户信息。
    - `TopBar`: 顶部栏，包含搜索框和面包屑/标题。
    - `MainLayout`: 核心内容区域的包装器。
- **Common Components (`components/common`)**: 高度复用的原子组件。
    - `RippleButton`: 带有点击水波纹效果的按钮，提升交互质感。
    - `LazyImage`: 支持懒加载和加载状态占位的图片组件。
    - `SearchTokenInput`: 支持标签化输入的搜索框核心组件。

### 3. 布局系统
应用使用嵌套布局系统：
1. **RootLayout**: 最外层，处理全局样式和 ThemeProvider。
2. **MainLayout**: 包含 `AppSidebar` (左) 和 `TopBar` (上) 以及内容区域 (中)。
3. **Page Layouts**: 具体页面内部的布局（如 `SearchPage` 的瀑布流布局）。

### 4. 状态管理与数据流
- **Server State**: 使用 `TanStack Query` (React Query) 管理 API 数据，处理缓存、加载状态和重新验证。
- **Global UI State**: 使用 `Zustand` (或 Context) 管理全局 UI 状态（如侧边栏折叠、主题切换）。
- **Local State**: 组件内部使用 `useState`/`useReducer` 管理局部交互状态。

### 5. 样式系统
- **Tailwind CSS**: 主要样式引擎，通过 Utility classes 快速构建 UI。
- **CSS Variables**: 在 `globals.css` 中定义主题变量（颜色、圆角等），支持动态主题切换。
- **Themes**: `styles/themes.ts` 定义了具体的主题配置（如 Light/Dark/OLED 模式）。

## 📝 开发规范

### 新增功能流程
1. 在 `src/features/` 下创建新目录。
2. 定义 API 接口 (`api/`)。
3. 创建业务组件 (`components/`)。
4. 在页面中引入使用 (`pages/`)。

### 组件开发原则
- **原子化**: 通用 UI 组件应尽量纯粹，不包含业务逻辑。
- **组合式**: 复杂组件通过组合原子组件构建。
- **类型安全**: 必须定义 Props 接口，避免使用 `any`。

### 路由与导航
- 路由定义在 `src/app/router.tsx`。
- 需要登录的页面使用 `ProtectedRoute` 包裹。
- 页面组件统一放在 `src/pages/` 下。
