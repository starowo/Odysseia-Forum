# 🏗️ 前端核心架构 (Core Architecture)

本项目采用 **Feature-Sliced Design (FSD, 功能模块化设计)** 作为基础架构方法论，结合 React 的组件化生态，实现高内聚、低耦合的可扩展前端业务。

## 1. 技术栈大盘

| 领域 | 核心技术 | 说明 |
| :--- | :--- | :--- |
| **视图层UI** | React 18, Vite | 现代化构建，支持 Fast Refresh 与高效打包 |
| **路由控制** | React Router v6 | 基于组件/Hook形式的前端路由分发 |
| **服务端状态管理** | `@tanstack/react-query` | 负责远程数据拉取、缓存、后台静默刷新、状态去重 |
| **客户端状态管理** | `zustand` | 轻量级、基于 Hooks 的全局 UI 状态流转 |
| **UI及样式** | Tailwind CSS, Framer Motion | 实用类名优先(Utility-First)样式，结合 Motion 实现丝滑动画 |
| **类型规范** | TypeScript, Zod | 全链路显式类型，使用 Zod 运行时数据有效性校验 |
| **通信层** | `axios`, `openapi-typescript` | 采用 RESTful 请求，并基于后端 OpenAPI (Swagger) 自动生成全局 TypeScript 接口类型 |

---

## 2. FSD (Feature-Sliced Design) 分层规范

本项目的 `src/` 目录严格遵循 FSD 分层逻辑。**层级越高（即越靠上），包含的具体业务逻辑就越多。**
> 核心原则 (依赖单向性): **上层模块可以引用下层或同层模块，但下层绝不能引用上层模块！**

从下至上（从最基础到最具体）的具体分层划分如下：

### 🧱 6. Shared (共享层)
**职责**：全局公用的基础设施、底层组件库（不包含任何业务数据）。
**内容**：
- `api/` (Axios 实例配置)
- `assets/` (全局静态资源图标等)
- `components/` (业务无关的基础 UI Kit，如 Button, Input, Modal骨架)
- `lib/` (工具库、格式化函数如 `utils.ts` 的 tailwind-merge)
- `types/` (全局类型定义，比如 `openapi.d.ts` 自动生成的 API 类型)

### 📦 5. Entities (实体层)
**职责**：代表应用中的核心业务对象及其展现（例如：User, Thread, Notification）。
**内容**：
- 实体相关的局部 UI (如 `UserProfileCard`, `ThreadItem`)
- 仅与自身实体相关的 React Query 钩子 (如 `useUser`, `useThreadList`)
- 单个实体的小切片 Zustand Store

### ⚙️ 4. Features (功能特性层)
**职责**：用户与应用交互的具体功能（往往需要改变状态或触发请求）。
**内容**：
- 表单提交模块 (如 `CreateThreadForm`, `AuthForm`)
- 复杂交互组件 (如 `LikeButton`, `FollowToggle`)
- 包含较重的业务逻辑钩子

### 🧩 3. Widgets (部件层)
**职责**：将 Features, Entities 和 Shared 组合而成的较大的、独立的页面级区块。
**内容**：
- 全局导航栏 (`Navbar`, `Header`)
- 复杂侧边栏 (`Sidebar`)
- 富文本编辑器组合区 (`RichTextEditorWidget`)

### 📄 2. Pages (页面层)
**职责**：处理路由、页面整体的布局装配，以及初始数据加载逻辑。
**内容**：
- 对应 Router 的顶层组件 (如 `HomePage`, `SearchPage`, `ProfilePage`)
- 负责获取路由参数(`useParams`)并向下传递给 Widgets/Features。

### 🚀 1. App (应用层)
**职责**：整个应用的初始化设置。
**内容**：
- 全局样式引入 (`index.css`)
- 全局 Provider 注册 (如 `QueryClientProvider`, `RouterProvider`, `ThemeProvider`)

---

## 3. 数据流流向 (Data Flow)

项目中存在两种主要的状态流转：

### 服务端状态 (Server State - React Query)
1. 在 `Shared/api` 或 `Entities/{Name}/api.ts` 中定义基础 Axios 请求函数。
2. 在 `Entities/{Name}/hooks.ts` 中封装 `useQuery` / `useMutation` 钩子。
3. `Widgets` 或 `Pages` 中直接调用这些钩子获取数据，不再使用 `useEffect` 手动获取并存入 state。

### 客户端状态 (Client State - Zustand)
1. 主要处理 UI 开关（如 Drawer 展开状态）、跨页面临时缓存（如未提交的草稿文本）。
2. 在 `Features` 或 `Entities` 下建立各自聚合的以 `useXxxStore` 命名的 zustand store。

通过这种架构，项目将复杂的页面解拆为了易于测试和维护的切片，大幅降低了大型 React 应用带来的“面条代码”风险。
