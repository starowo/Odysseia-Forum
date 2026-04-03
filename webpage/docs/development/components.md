# 🧱 组件开发指南 (Components)

在 Feature-Sliced Design (FSD) 架构下，组件被横向切割为了不同级别的重用度与业务耦合度。本指南规定了组件应该如何被放置和开发。

## 1. 基础 UI 组件 (`Shared/ui`)

放置在 `src/shared/ui/` 中的组件是**完全不包含业务逻辑的纯展示组件**（Dumb Components）。

### 1.1 设计要求
- **零外部状态**: 不允许引入任何 `useQuery`、`useStore` 获取远端数据或全局状态。
- **Props 驱动**: 外界通过 props 将需要的数据传入，通过回调 (`onClick`, `onChange` 等) 通知变更。
- **组合封装**: 优先使用现有的组件进行二次封装（例如封装后的 `RippleButton` 或是具备通用业务无关逻辑的 `SearchTokenInput`）。

**现有共享 UI 示例**:
- `MarkdownText`: 负责安全地渲染 Markdown，不管数据来源。
- `LazyImage`: 负责图片的懒加载与淡入，支持任何 src。
- `ThemeToggle`: 纯粹改变全局背景和状态的主题切换开关。

## 2. 业务组件 (`Features` & `Widgets`)

### 2.1 Widgets (挂件)
Widgets 通常是页面中非常大的一个功能区块（往往具备独立的请求和状态逻辑可以实现自我驱动）。
- 目录示例: `src/widgets/layout/TopBar.tsx`, `src/widgets/sidebar/LeftSidebar.tsx`
- **目的**: 让页面层 (`Pages`) 的代码极度清爽，Page 只负责像搭积木一样将 Widget 拼起来。

### 2.2 Features (特性功能组件)
处理特定用户用例的组件。比如：发帖表单、点赞按钮。
他们应该**自带该功能的全部逻辑**。
- 如果你要封装一个 `LikeButton`，它不应该把网络请求暴露给父级。相反，`LikeButton` 自己读取传入的 `threadId`，在自己内部调用 `useMutation(...)`，这样任何地方只要放置这个 `<LikeButton threadId={123} />` 就能工作，做到绝对解耦。

## 3. 组件性能与渲染优化

由于 React 在父级渲染时会级联渲染所有子级，在开发组件时请注意：
1. **优先提取状态**: 把那些频繁变动的状态拆解并封装到独立的子组件中，不让大范围布局一起陪着渲染（下放 State）。
2. 使用 `useMemo` 与 `useCallback` 来包裹庞大计算或者传递给子组件（如果是 `React.memo`）的函数。
3. 如果要在视图上绑定大量的循环数据呈现（如无限加载的帖子列表），请利用 `@tanstack/react-virtual` 虚拟大列表来渲染，它能将 DOM 元素保持在几十个的数量级，极大优化页面重排效率。
