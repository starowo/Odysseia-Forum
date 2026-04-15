# 🔄 状态管理指南 (State Management)

在复杂的前端应用中，清晰地划分不同类型的数据状态是保证项目可维护性的关键。本项目将状态严格划分为 **服务端状态 (Server State)** 和 **客户端状态 (Client State)** 两种。

## 1. 核心理念与技术选型

| 状态类型 | 职责描述 | 技术栈 |
| :--- | :--- | :--- |
| **Server State** | 与后端数据库保持同步的数据（如：帖子列表、用户资料），具有异步、需要缓存、会被其他用户更改的特性。 | `@tanstack/react-query` |
| **Client State** | 纯前端的交互状态（如：模态框是否展开、搜索面板输入的缓存字、当前选中的本地标签栏）。 | `zustand` |

> ⚠️ **强制规范**：绝对禁止使用 `zustand` 或 `useState` 搭配 `useEffect` 来手动发请求缓存后端返回的业务数据。服务器返回的数据流统一必须通过 React Query 管理。

## 2. Server State (React Query) 规范

`@tanstack/react-query` 充当了我们在浏览器中的 "数据同步代理"。

### 2.1 基础调用流
1. 在 `Shared/api` 中通过 `axios` 编写基础数据请求函数（仅返回Promise）。
2. 在 `Entities` 内部封装专属的自定义 Hook。例如 `useThreadList`。
3. 在业务组件中直接引入该自定义 Hook 进行使用。

### 2.2 设计原则
- **查询键 (Query Keys) 必须序列化且具语意**: 形如 `['threads', 'list', { filter: 'hot' }]`。
- **staleTime (数据陈旧时间)**: 必须显式设置。默认不要是 0，可以设定为 `1000 * 60` (1分钟) 甚至更长，减少网速带宽压力。
- **并发与重试**: React Query 默认会在组件 Focus 或网络重新连接时静默刷新。

## 3. Client State (Zustand) 规范

`zustand` 是目前最轻量、没有样板代码的 React 状态管理库。
在本项目中，Store 文件一般放置在 `src/features/{featureName}/store/` 目录中。

### 3.1 定义规范

```typescript
import { create } from 'zustand';

// 1. 定义状态和动作的接口
interface SearchUIState {
  // Banner UI 状态
  isMainBannerVisible: boolean;
  activeBannerId: string | null;

  // Actions
  setMainBannerVisible: (visible: boolean) => void;
  setActiveBannerId: (bannerId: string | null) => void;
}

// 2. 创建 store
export const useSearchStore = create<SearchUIState>()((set, get) => ({
  isMainBannerVisible: true,
  activeBannerId: null,

  setMainBannerVisible: (visible) => {
    if (get().isMainBannerVisible === visible) return;
    set({ isMainBannerVisible: visible });
  },

  setActiveBannerId: (bannerId) => {
    if (get().activeBannerId === bannerId) return;
    set({ activeBannerId: bannerId });
  },
}));
```

### 3.2 使用规范 (防重渲染)

由于 Zustand 是外部 store，在组件中使用时请**仅提取当前组件真正需要的字段**。这样可以避免不相关的状态改变触发整个组件的重渲染。

✅ 正确用法（仅订阅可见性状态）：
```tsx
const isMainBannerVisible = useSearchStore((state) => state.isMainBannerVisible);
const setMainBannerVisible = useSearchStore((state) => state.setMainBannerVisible);
```

❌ 错误用法（会导致任何 SearchUIState 其他值的变化都引发组件刷新）：
```tsx
const store = useSearchStore(); 
```

### 3.3 URL 作为状态 (URL as State)
对于诸如搜索参数（搜索词、筛选渠道、标签、作者等）的场景，**强制使用 URL 参数 (`URLSearchParams`) 代替 Zustand 作为数据源**。
- 好处: 状态可分享、支持浏览器前进后退、解耦 UI Store 与请求逻辑。
- 示例: 在 `src/features/search/hooks/useSearchParams.ts` 中，通过暴露 `useSearchURLParams` 钩子解析并维护 `query`, `channel`, `sortMethod` 等查询参数。独立的业务逻辑（如 `src/features/search/store/previewStore.ts` 帖子预览）**已强制从通用 UI Store 中抽离解耦**，只保留最核心的纯 UI 控制逻辑（如 Banner 可见性）在 `searchStore` 中。

### 3.4 状态的局部化
尽量只将 `跨组件通信` 或者 `页面级需要维持的草稿流` 放入 `zustand`。普通的单组件内部开关（如某个下拉菜单是否展现），优先使用 React 原生的 `useState`。
