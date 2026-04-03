# 🎨 UI 样式与设计指南 (UI & Style Guide)

本项目使用 **Tailwind CSS** 作为原子化 CSS 引擎，结合 **CSS Variables (自定义属性)** 来实现流畅的主题切换和高度一致的设计系统。

## 1. 核心设计体系

我们在 `tailwind.config.js` 扩展了默认体系，并与 `index.css` 中的全量 CSS Variables 绑定，具有强烈的 **shadcn/ui** 风格。

### 1.1 主题色 (Theming)
所有的颜色统一不使用硬编码的 Hex 值，而是使用 HSL 变量。
- `bg-background` / `text-foreground`: 页面主背景与主文本色。
- `bg-primary` / `text-primary-foreground`: 核心强调色（通常是品牌色，如主按钮）。
- `bg-secondary`: 次要强调色（如次级按钮、辅助说明区块）。
- `bg-muted`: 极化反差极小的静音底色（如禁用的按钮或是底纹）。
- `bg-accent`: 悬浮态(Hover)高亮色。
- `bg-card` / `bg-popover`: 卡片与浮窗容器底色。
- `bg-destructive`: 警告或危险操作颜色（如红色删除按钮）。

### 1.2 排版与尺寸 (Typography & Spacing)
我们定义了一套 `od-` 前缀的专属变量进行语义化约束。

- **字号**: `text-od-xs`, `text-od-sm`, `text-od-base`, `text-od-lg`。
- **字重**: `font-od-normal`, `font-od-medium`, `font-od-bold`。
- **间距**: 
  - 基础：`p-od-sm`, `m-od-md`, `gap-od-lg`（采用 `od-xs` 到 `od-xl` 梯队）。
  - 语义：`p-od-modal-p` (设定模态框内边距), `gap-od-card-gap` (卡片内元素的标准间距)。

> **开发要求**: 尽可能使用 `od-` 系列的间距和字号，以确保全局视觉在暗黑模式、移动端响应式下保持绝对统一。

## 2. 样式编写工具链

### 2.1 tailwind-merge 与 clsx
为了避免 Tailwind CSS 的类名冲突（尤其是在封装组件，接收外部 `className` 时），必须使用 `cn` 工具函数。

```typescript
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**示例**:
```tsx
// 即使外部传入了 bg-red-500，twMerge 也会正确地覆盖掉内部的 bg-primary
<div className={cn("bg-primary text-white p-4", props.className)}>
```

### 2.2 class-variance-authority (CVA)
对于多形态的组件（如 Button 拥有 primary, secondary, outline 多种 `variant`，以及 sm, lg 等 `size`），使用 `cva` 来管理状态变体。

```tsx
import { cva } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        outline: "border border-input hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)
```

## 3. 动画 (Animations)
项目中使用了 `tailwindcss-animate` 插件提供基础动画类名（如 `animate-in`, `fade-in`, `zoom-in` 等）。
如需更复杂的弹性过渡或是物理运动，应在 `Features` 层面使用 `framer-motion`。
