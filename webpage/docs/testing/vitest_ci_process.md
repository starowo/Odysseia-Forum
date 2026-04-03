# 🧪 测试与自动化检测 (Testing & CI)

本项目的前端采用 **Vitest** 结合 **React Testing Library** 作为测试套件。Vitest 与 Vite 共享同一套配置，具备极快的执行速度和原生 ESM 支持。

## 1. 测试运行规范

在 `package.json` 中配置了以下快捷指令：
- `npm run test` 或 `pnpm run test`: 执行全部测试并在文件改变时热更新 (Watch 模式)。
- `npm run test:ui`: 启动提供可视化的测试管理面板 (Vitest UI)。
- `npm run test:coverage`: 执行单次测试并输出基于 `v8` 引擎的代码覆盖率报告。

## 2. 单元测试编写指南

### 2.1 引入 `test-utils`，而非原生库
由于我们的组件常常依赖路由 (`useNavigate`) 和状态缓存 (`useQuery`)，使用默认的 renders 会立刻报错。
我们封装了一个全局包含 Context Provider 的工具函数：

✅ 正确用法:
```tsx
// 从内部的 custom render 工具统一导入，不要从 '@testing-library/react' 导入
import { render, screen } from '@/tests/test-utils';
import MyComponent from './MyComponent';

test('它应该成功渲染', () => {
  render(<MyComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```

### 2.2 测试文件的位置约定
测试文件应遵循 **就近原则 (Colocation)**，将其放置在被测试组件的同一层级文件夹内，并以 `.test.tsx` 或 `.spec.ts` 结尾。
例如：
```text
src/features/auth/
 ├── LoginForm.tsx
 ├── LoginForm.test.tsx  <-- 这个文件就是 LoginForm 的测试
 └── hooks/useAuth.ts
```

## 3. Mock 机制 (网络请求与外部依赖)

测试时绝不允许真的发起网络请求。前端通常面临两种层面的 mock：
1. **Mock 钩子 (Hook级别的 Mock)**：最简单的方法是使用 Vitest 原生的 `vi.mock()` 直接拦截 `useQuery` 自定义钩子的返回值。
2. **Mock 网络 (MSW - Mock Service Worker)**: 针对高度依赖原生 Axios Fetch 操作的深度组件，在 `src/tests/setup.ts` 中可以配置 MSW 在网络层级劫持真实请求并返回 JSON。

## 4. CI/CD 流水线检查预设
由于团队经常涉及快速迭代，强建议项目托管（如 GitHub）启用如下自动化的合并前检视（PR Check 流水线）：
1. **代码风格约束**: 每次 PR 执行 `pnpm run lint` 与 `pnpm run format` 检查。
2. **TypeScript 类型校验**: 执行 `tsc --noEmit` 拦截潜在类型隐患。
3. **单元测试网关**: 强制运行 `pnpm run test:coverage`，任何断言失败都会拦截代码合并。
4. **编译期检测**: 执行 `pnpm run build` 保障最终编译成功。
