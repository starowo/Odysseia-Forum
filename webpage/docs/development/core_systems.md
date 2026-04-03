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
