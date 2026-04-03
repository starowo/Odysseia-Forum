# 🎨 UI 样式与设计指南 (UI & Style Guide)

本项目使用 **Tailwind CSS** 作为原子化 CSS 引擎，结合 **CSS Variables (`--od-*`)** 来实现流畅主题切换、语义层级和透明风格。

## 1. 核心设计体系
我们不只是设计前端,我们是在设计艺术,艺术是融会贯通的,
我们采用 `Tailwind + od-token` 的双轨体系：

- Tailwind 负责布局、间距、响应式。
- `--od-*` 负责颜色语义、字重字号、透明与磨砂策略。

### 1.1 主题色与语义色 (Theming)

所有颜色优先使用语义变量，不直接硬编码 Hex。

- **基础背景层**：`--od-bg` / `--od-bg-secondary` / `--od-bg-tertiary`
- **容器层**：`--od-card` / `--od-card-hover`
- **边界层**：`--od-border` / `--od-border-strong`
- **文本层级**：
  - `--od-text-primary` / `--od-text-secondary` / `--od-text-tertiary`
  - `--od-text-heading` / `--od-text-label` / `--od-text-meta`
  - `--od-text-link` / `--od-text-value` / `--od-text-emphasis`
- **状态与高亮**：`--od-accent` / `--od-accent-hover` / `--od-success` / `--od-warning` / `--od-error` / `--od-info`

> **开发要求**: 组件实现时，颜色来源优先顺序是：`--od-*` > 语义类 > Tailwind 临时原子类。

### 1.2 排版与层级 (Typography & Hierarchy)

本项目强调“**字重优先**”的层级表达，避免只靠颜色区分主次。

- **语义字号变量**：`--od-type-title` / `--od-type-label` / `--od-type-body` / `--od-type-meta` / `--od-type-code`
- **语义字重变量**：`--od-weight-strong` / `--od-weight-medium` / `--od-weight-regular`
- **推荐语义类**：
  - `.od-text-title`：主标题
  - `.od-text-label`：字段名/分组名
  - `.od-text-body`：正文
  - `.od-text-meta`：元信息
  - `.od-text-code`：数值/代码/ID

> **开发要求**: 一级信息先提升字重，再调整字号，最后才是颜色增强。

## 2. 无框流体风格 (Borderless Fluid)
卡片或者不同颜色的主题嵌套绝对不可以超过三层
本项目不鼓励“卡片套卡片”的厚重层级，优先无框流体表达。
- `.od-fluid-panel`：弱容器（弱边界、轻背景）
- `.od-fluid-section`：无框分段
- `.od-fluid-divider`：细分割线
- `.od-ghost-input`：底线输入风格
直接把字放在背景上,不需要容器,这也是现在大部分互联网公司的设计风格
简单,少即是多,只要你的文字排版够好,善于用字色,字重,字体去作为你的设计语言,没有边框又怎么样


> **开发要求**: 高密度页面优先依靠排版与间距建立层级，不靠边框堆叠。

## 3. 透明与磨砂玻璃 (Transparency & Glass)

### 3.1 分层规则

当前透明主题使用统一分层：

1. **底层**：`od-operation-base`（与背景图直接对接，可启用毛玻璃）
2. **操作层**：`TopBar` / `Sidebar`（继承底层色，不单独制造磨砂）
3. **内容层**：`od-content-surface`（只用透明混色）
4. **浮层**：`od-floating-glass`（下拉、预览、通知、modal）

### 3.2 性能规则（必须）

磨砂是高成本效果，必须控制预算：

- 大面积磨砂仅允许底层 1 层。
- 浮层磨砂只用于小面积弹层。
- 其余层使用透明混色，不叠加 `backdrop-filter`。

> **一句话规则**: 不是所有透明层都需要毛玻璃。

### 3.3 透明度算法目标

- 透明主题整体偏浅，避免内容区明显压暗。
- TopBar / Sidebar / 内容区应有层级，但差值不应突兀。
- 背景图主体常在内容区时，内容层应保持通透与可读平衡。

## 4. 高亮色使用规范 (Accent Usage)

`--od-accent` 用于“交互焦点”，不是通用文本色。

- ✅ 用于：激活状态、焦点边框、主 CTA、关键指标
- ⚠️ 谨慎：大面积背景铺色
- ❌ 避免：正文长段落着色

推荐模式：

- 常态文本：`text-[var(--od-text-secondary)]`
- 激活文本：`text-[var(--od-accent)]` + 轻量背景（如 `/10`）

## 5. 样式编写工具链

### 5.1 tailwind-merge 与 clsx

封装组件（接收外部 `className`）必须使用 `cn`，避免冲突。

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**示例**:
```tsx
<div className={cn('od-fluid-panel p-4', props.className)}>
```

### 5.2 class-variance-authority (CVA)

多变体组件（Button/Tag/Tab/Badge）使用 `cva` 管理 `variant` 和 `size`。

## 6. 动画与过渡 (Animations)

- 基础动画：`tailwindcss-animate`（如 `animate-in`, `fade-in`）。
- 复杂交互：`framer-motion`。
- 全局主题过渡仅在主题切换时启用，不在滑杆实时调节中启用。

## 7. 开发禁忌与检查清单

### 7.1 禁忌 (Don'ts)
- 卡片或者不同颜色的主题嵌套超过三层
- 禁止新增与 `--od-*` 并行的私有主题系统。
- 禁止在主内容大容器叠加多层 `backdrop-filter`。
- 禁止把圆角、滚动、重特效塞进同一超大节点。
- 禁止把 `--od-accent` 当通用正文色。

### 7.2 提交前检查 (Checklist)

1. 是否优先使用 `--od-*` 语义变量。
2. 是否用字重+字号体现层级（而不是只靠颜色）。
3. 是否把磨砂限制在底层与浮层。
4. TopBar / Sidebar 是否继承统一背景来源。
5. 移动端 sidebar 是否可覆盖 topbar。
