# 🎨 UI 样式与设计指南 (UI & Style Guide)

本项目使用 **Tailwind CSS** 作为原子化 CSS 引擎，结合 **CSS Variables (`--od-*`)** 来实现流畅主题切换、语义层级和透明风格。

## 1. 核心设计体系
我们不只是设计前端,我们是在设计艺术,艺术是融会贯通的,
我们采用 `Tailwind + od-token` 的双轨体系：
无框流体不是毛玻璃,它比毛玻璃更简洁,更优雅,甚至和毛玻璃不冲突,它主要涉及的是背景色和文字排版
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

### 2.1 分割线不是边框替代品，而是版式语言

当我们主动去掉 section 容器、浅背景块和重边框以后，页面必须依靠更明确的“排版分段”来建立结构。
分割线的职责不是把内容框起来，而是把阅读节奏切开。

- 分割线优先使用与文字体系同源的颜色，而不是额外造一套灰线系统。
- 分割线建议使用“**两边淡，中间深**”的渐变线，而不是通栏等粗细的实线。
- 分割线要配合标题、留白、kicker、小标题一起工作，不要单独承担结构任务。
- `FluidDivider` 这类组件应该是页面级/分组级 primitive，不应和额外的 section 边框同时叠加。

> **开发要求**: 同一个 section 切换点只能有一种主要分割方式，避免“divider + border-top”重复出现。

### 2.2 页面结构先分“段”，再分“块”

无框流体不是没有结构，而是：

- 页面先由 **Hero / 标题区 / 主内容段 / 辅助说明段** 构成
- 段与段之间优先用留白、短 divider、字重差建立结构
- 只有真正有交互负担的实体，才允许拥有 surface

优先顺序：

1. 字号与字重
2. 文本颜色深浅
3. 留白和段落节奏
4. divider
5. 最后才考虑轻量背景

> **开发要求**: “标题区域”“说明区域”“筛选标题行”默认不加背景容器，先尝试直接写在页面背景上。

### 2.3 轻 surface 只留给真正的交互实体

下列元素可以拥有轻量 background / surface：

- 资源卡片 / 帖子卡片 / 书单卡片
- 浮层 / 预览层 / modal / dropdown
- 输入控件 / 复杂表单块 / 局部状态块

下列元素默认不应该拥有独立盒子：

- 页面标题
- 分组标题
- 分区说明文案
- rail 标题头
- 普通统计标题行

> **开发要求**: 不要为了“看起来像有设计”给标题行额外包一层浅暗块。

### 2.4 hover 的重点是图标和文字，不是边缘发光

按照当前确定的风格，hover 不以“边框高亮”作为主反馈，而是优先强调：

- 图标颜色变化
- 标题/主文本颜色变化
- 当前值、状态值的强调色变化
- 极轻的背景浮动或位移

推荐模式：

- 常态：边框透明或极弱
- hover：文字/图标提亮，必要时补一层极轻背景
- active：继续强调文字与图标，不把边框做成主角

> **开发要求**: 选择器、导航项、过滤项、设置项的 hover 尽量避免“边框先亮起来”。

### 2.5 单栏信息编排优先于后台式双栏控制台

对于设置页、搜索筛选页、用户偏好页这类“连续阅读 + 调整”的页面：

- 默认优先单栏信息流
- 避免为了“专业感”堆出双栏控制台布局
- 移动端必须自然继承同一节奏，而不是事后再打补丁

当信息量较大时，优先使用：

- section kicker
- section title
- helper note
- current value / emphasis
- inline options / row options

而不是：

- 一整屏均质的小按钮盒子
- 大量浅暗小面板并列
- 一看就是“设置后台”的多宫格控制布局

> **开发要求**: 设置类页面必须先设计阅读节奏，再放控件，不要直接从控件反推布局。

### 2.6 字体层级、文字深浅、强调色必须主动使用

如果没有边框和块面，排版就必须承担设计责任。
所以页面实现时必须主动使用以下维度，而不是默认都写成差不多的 `text-sm`：

- **标题**：更大字号 + 更重字重
- **kicker / label**：更小字号 + uppercase/tracking + label 色
- **说明文字**：更浅颜色 + 更松行高
- **当前值 / 当前模式**：使用 `--od-text-value` / `--od-text-emphasis`
- **激活项**：优先通过图标和文本着色区分

推荐语义分工：

- `--od-text-primary`：主标题 / 关键内容
- `--od-text-secondary`：说明文案 / 正文辅助信息
- `--od-text-tertiary`：meta / 次级提示
- `--od-text-label`：kicker / 小标签 / 分组提示
- `--od-text-value`：数值 / 当前值 / 可量化指标
- `--od-text-emphasis`：模式提示 / 方向性强调 / 当前建议

> **开发要求**: 每个页面至少要明确 title / note / meta / value 四类文本角色，不能所有文案都落在同一个层级上。


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

补充说明：

- `--od-accent` 更适合承担“交互焦点”和“激活状态”
- `--od-text-label`、`--od-text-value`、`--od-text-emphasis` 应承担更多信息层级角色
- 不要把所有有区别的文本都塞给 `accent`

> **开发要求**: 页面做层级时，优先想 `label / value / emphasis` 能否解决，而不是所有重点都刷成 accent。

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
6. 页面标题、分组标题、说明文案是否仍被不必要的浅背景容器包裹。
7. 是否存在 divider 与 border-top 重复出现的情况。
8. hover 是否优先强调图标/文字，而不是边框。
9. 设置页/筛选页是否真的设计了文本层级，而不是只排列了一堆控件。
