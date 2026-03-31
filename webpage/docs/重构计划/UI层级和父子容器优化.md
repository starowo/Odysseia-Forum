# Odysseia 前端 UI 层级和父子容器优化

## 1. 目标

这篇文档只讨论三件事：

- 哪些容器负责布局
- 哪些区域允许滚动
- 哪些浮层必须脱离普通文档流

V2 要从“网页堆叠思维”转成“应用壳思维”。

---

## 2. 当前问题

## 问题一：布局职责重复

当前布局职责分散在：

- [`RootLayout`](../../src/components/layout/RootLayout.tsx:5)
- [`MainLayout`](../../src/components/layout/MainLayout.tsx:14)
- [`SearchPage`](../../src/pages/SearchPage/index.tsx:453)

结果是：

- 有统一布局组件，但最核心页面没有完全使用它
- 页面自己又复制一套 Sidebar 加 Main 的结构
- 后面越改越容易出现不同页面行为不一致

---

## 问题二：滚动域不够明确

当前页面大量依赖普通页面滚动思路。

风险是：

- sticky 和 fixed 会越来越多
- 浮层更容易和滚动冲突
- 移动端更容易出现滚动穿透
- 页面结构越复杂，越难判断谁在滚

---

## 问题三：浮层挂载点分散

当前项目里这些都属于浮层或准浮层：

- 搜索建议
- 通知中心
- 帖子预览
- 浮动 banner
- 看板娘

如果继续各自找地方挂，会逐渐进入 z-index 混乱。

---

## 3. V2 布局原则

1. 全站只保留一个主应用壳
2. 页面组件不再自建主布局
3. 主滚动容器唯一
4. 浮层不依附普通内容容器层级
5. z-index 使用统一分层，不允许随意发明

---

## 4. 标准布局树

推荐结构：

```text
AppRoot
  AppShell
    SidebarLayer
    MainColumn
      TopBarLayer
      MainScrollArea
    OverlayRoot
    GlobalAssistLayer
```

### 说明

- `AppRoot`
  - 最外层应用根节点
- `AppShell`
  - 全站主骨架
- `SidebarLayer`
  - 侧边导航和频道区
- `MainColumn`
  - 顶栏加内容区
- `TopBarLayer`
  - 页面头部操作区
- `MainScrollArea`
  - 唯一主滚动区
- `OverlayRoot`
  - Dialog、预览、下拉等浮层
- `GlobalAssistLayer`
  - toast、看板娘、全局提示类能力

---

## 5. 各容器职责

## [`RootLayout`](../../src/components/layout/RootLayout.tsx:5)

V2 职责：

- 作为应用外层根节点
- 提供全局辅助层挂载点
- 不承载页面业务布局细节

## [`MainLayout`](../../src/components/layout/MainLayout.tsx:14)

V2 职责：

- 升级成真正的 App Shell
- 统一侧边栏、顶栏、主内容区结构
- 页面只把内容插进去

## 页面组件

例如 [`SearchPage`](../../src/pages/SearchPage/index.tsx:40)：

V2 不再负责：

- 自建侧边栏
- 自建主布局
- 自己决定全局容器层级

页面只负责：

- 读取状态
- 编排 section
- 渲染内容

---

## 6. 滚动规则

### 规则一：主滚动区唯一

建议只允许 `MainScrollArea` 纵向滚动。

### 规则二：Sidebar 是否滚动必须明确

如果侧边栏内容可能超长，可以让侧边栏内部独立滚动，但不能和页面主滚动语义混淆。

### 规则三：浮层内部滚动局部解决

Dialog、通知面板、预览面板如果内容过长，自己内部滚动，不借用页面滚动。

### 规则四：移动端优先防滚动穿透

移动端抽屉、预览、筛选面板打开时，底层主滚动应被锁住。

---

## 7. 哪些组件必须进入 overlay 体系

以下组件不应继续作为普通子节点随处挂载：

- 搜索建议面板
- 通知中心
- 帖子预览层
- Dialog 和 Drawer
- Tooltip 和 Dropdown

原因很简单：

- 避免被父容器裁剪
- 避免被局部 `overflow` 干扰
- 避免与页面层级竞争

---

## 8. z-index 规范

统一采用分层命名，不再让组件自行决定。

### 推荐层级

- 基础内容层：0 到 10
- 吸顶层：20
- 导航层：30
- 遮罩层：40
- 模态层：50
- 全局提示层：60+

### 规则

- 普通页面内容不能抢导航层
- 局部浮层不能抢模态层
- toast、看板娘这类全局辅助层必须固定在最高一档

---

## 9. 当前文件对应改造点

## [`SearchPage`](../../src/pages/SearchPage/index.tsx:453)

要移除：

- 页面内部重复布局结构
- 页面直接持有侧边栏开关和容器结构

## [`TopBar`](../../src/components/layout/TopBar.tsx:36)

要调整：

- 下拉与高级面板的层级策略
- 未来必要时走 Portal

## [`NotificationCenter`](../../src/features/notifications/components/NotificationCenter.tsx:27)

要调整：

- 从侧边栏附属面板，提升到统一 overlay 体系中的一种面板

## [`GlobalThreadPreview`](../../src/app/App.tsx:64)

要调整：

- 保持全局预览思路
- 但挂载位置和状态来源要更明确

---

## 10. 验收标准

满足以下条件，才算布局和层级重构完成：

1. 搜索页不再重复实现主布局
2. 全站主滚动区唯一
3. 浮层不会被父容器裁剪
4. 主要浮层不再依赖局部容器层级碰运气显示
5. 移动端弹层打开时，底层不发生明显滚动穿透
6. 不再出现到处写超高 z-index 的情况

---

## 11. 和其他文档的关系

- 架构整体见 [`总体架构重构计划.md`](./总体架构重构计划.md)
- 状态边界见 [`状态管理与数据流重构.md`](./状态管理与数据流重构.md)
- 当前问题定位见 [`现状问题清单与代码映射.md`](./现状问题清单与代码映射.md)
