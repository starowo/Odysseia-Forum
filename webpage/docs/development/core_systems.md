# ⚙️ 核心系统设计 (Core Systems)

此文档总结了除数据流机制外，支撑起整个前端运转的几大核心系统的设计模式。

## 1. 路由系统 (Routing)

项目采用基于 `react-router-dom` v6 搭建的路由体系。在 `src/app/` 或 `src/pages/` 的顶层定义有整个路由大树。

### 1.1 嵌套路由与 Layout
我们使用了嵌套路由的概念：
```tsx
<Route path="/" element={<RootLayout />}>
  <Route index element={<HomePage />} />
  <Route path="/search" element={<SearchPage />} />
</Route>
```
所有的普通页面被嵌入到了 `RootLayout`（主布局）中。
- `RootLayout` 负责渲染全局的 Sidebar，搜索顶栏、背景图容器等。
- `<Outlet />` 是各个具体 `Page` 组件挂载的渲染热区。
利用这个模式避免了页面跳转带来的整个外框的反复卸载与重绘。

### 1.2 路由懒加载 (Code Splitting)
为了加快首屏（FCP/LCP）加载速度，大型页面通过 `React.lazy()` 进行异步代码分割：
```tsx
const ProfilePage = lazy(() => import('@/pages/UserProfilePage'));
```
路由层用 `<Suspense fallback={<Loader />}>` 进行包裹。如果你新加了一个特别庞大的独立页面组件，**强制使用懒加载形式注册路由**。

## 2. 身份验证守卫 (Auth Guard)

我们的权限验证不是仅仅靠后端返回 401 报错才拦截。
在路由体系中具备 `ProtectedRoute` 高阶组件（或 Wrapper）。
- 检测不到有效认证状态时，拦截去往敏感路由（如 `/me`）的访问，展示提示或者自动触发到 Discord OAuth2 的登录流程。

## 3. 错误捕获 (Error Boundaries)

应用需要使用 Error Boundary（错误边界）接管白屏崩溃。
无论是路由层面，还是某个渲染复杂的 Widget，外部可以嵌套容错机制组件，确保组件因为不可控数据结构崩溃时，不至于导致整个浏览器白屏，而是局部显示兜底 UI。

## 4. 主题与持久化 (Theme Persistence)

黑/白模式切换由 `ThemeToggle` 控制。此状态属于全局客户端偏好：
- 优先读取 `localStorage` 中记录的用户偏好（如 `theme: dark`）。
- 否则读取浏览器系统的时区或 `prefers-color-scheme`。
我们将 class `dark` 动态注入至 `HTML` 根节点上控制整个 Tailwind 变量生效。

## 5. 搜索系统与 URL 状态驱动

搜索系统目前完全依靠 **URL Search Params** 进行状态同步，以保障用户可以自由分享其搜索或过滤状态，并避免状态管理的冗余与数据不一致。

### 5.1 分词器驱动 (searchTokenizer)
搜索词输入支持高级语法的精确匹配与条件剥离，前端使用 `src/shared/lib/searchTokenizer.ts` 作为统一解释器：
- **可用语法**: `$tag:xxx$`, `-$tag:xxx$`, `$author:xxx$`, `-$author:xxx$`, `$channel:xxx$`。
- **协议转换**: 当用户在 `TopBar` 键入字符或点击特定面板（如 `SearchFilterPanel`）按钮时，工具函数（如 `addToken`, `removeToken`）会改变全局查询字符串，随后 `tokenizeSearchPayload` 会将长字符串打散为 API 可接受的数据结构（`includeTags`, `excludeTags`, `includeAuthors`, `excludeAuthors`, `channels` 等）。
- **向后兼容**: 为了兼容旧版未带 `$` 符号的语法，分词器中引入了 `migrateLegacySyntax` 函数，在处理 URL 查询参数时，它会自动把类似 `author:xxx` 的格式标准化为 `$author:xxx$`。

### 5.2 参数层 (`useSearchURLParams`)
`src/features/search/hooks/useSearchParams.ts` 中的 `useSearchURLParams` 钩子解析并暴露经过封装合并后的过滤状态，组件使用该钩子修改参数会自动触发 React Router 的导航方法，进而引发整个订阅此 Hooks 的查询模块重刷。
