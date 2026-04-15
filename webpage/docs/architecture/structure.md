# 📁 目录结构说明 (Directory Structure)

本文件详细描述了基于 FSD (Feature-Sliced Design) 的前端代码库业务结构。配合 `core_architecture.md` 阅读，可快速厘清现有文件的存放位置与逻辑边界。

## 1. 完整目录树

```text
Odysseia-Forum-Main/
├── webpage/                          # React 前端根目录
│   ├── src/
│   │   ├── app/                    # [App 面向应用层] 全局配置、路由拓扑、顶层 Provider
│   │   │   ├── providers/          # 错误边界、路由守卫、QueryClientProvider
│   │   │   ├── themes/             # 主题上下文
│   │   │   ├── App.tsx             # 基础包裹组件
│   │   │   └── router.tsx          # 路由树定义
│   │   │
│   │   ├── pages/                  # [Pages 面向路由层] 每个路由对应的容器页面
│   │   │   ├── SearchPage/         # 搜索主页
│   │   │   ├── FollowsPage/        # 关注中心
│   │   │   └── ...
│   │   │
│   │   ├── widgets/                # [Widgets 面向区块层] 组装多个特性的庞大独立 UI 块
│   │   │   ├── layout/             # 核心框架布局 (TopBar, AppSidebar)
│   │   │   ├── sidebar/            # 侧边栏挂件
│   │   │   └── thread-preview/     # 面向全局的帖子预览浮层组合
│   │   │
│   │   ├── features/               # [Features 面向行为层] 带有明确业务闭环和网络读写的特性操作
│   │   │   ├── auth/               # 认证流程 (登录守卫、会话管理)
│   │   │   ├── banner/             # 轮播图管理 (Banner 申请交互)
│   │   │   ├── booklists/          # 书单系统 (书单增删改查、帖子批量加入)
│   │   │   ├── follows/            # 关注系统 (未读状态拉取、更新中心)
│   │   │   ├── mascot/             # 吉祥物面板 (全局提示、互动气泡)
│   │   │   ├── notifications/      # 通知中心 (整合提醒、未读汇总)
│   │   │   ├── plaza/              # 广场大盘
│   │   │   ├── preferences/        # 用户偏好设置 (搜索习惯、标签过滤黑白名单)
│   │   │   ├── search/             # 搜索中枢 (分词器、URL状态同步、API桥接)
│   │   │   └── threads/            # 帖子行为总成 (点赞、转发、预览流等动作钩子)
│   │   │
│   │   ├── entities/               # [Entities 面向实体层] 以特定业务模型为核心的对象与轻量视图
│   │   │   ├── thread/             # 帖子骨架与数据结构 (ThreadCard)
│   │   │   ├── user/               # 用户卡片 (AuthorAvatar)
│   │   │   └── channel/            # 频道展示区
│   │   │
│   │   ├── shared/                 # [Shared 面向共享基建] 纯粹的通用组件与核心底层逻辑
│   │   │   ├── ui/                 # 原子组件大盘 (Button, Tooltip, LazyImage)
│   │   │   ├── lib/                # 纯函数支持 (Tailwind合并器, 工具类)
│   │   │   ├── hooks/              # 非业务相关的 React钩子 (页面视窗感知等)
│   │   │   ├── api/                # Axios 总实例与拦截器配置
│   │   │   ├── styles/             # Tailwind 全局配置与入口
│   │   │   └── types/              # TS 声明区 (包括 OpenAPI 自动生成接口)
│   │   │
│   │   ├── assets/                 # 静态字体、图标等切图资源
│   │   └── main.tsx                # React 的挂载原生入口
│   │
│   ├── tsconfig.json               # 核心编译策略
│   └── vite.config.ts              # 核心服务运行与代理策略
```

## 2. 核心功能分布

在日常开发中，如果你需要修改某一个特定的功能，可以通过如下规律快速定界：

- **搜索与列表展现**: 主要被汇聚在了 `src/features/search/`。通过 `searchTokenizer` 提供分词功能，利用 `useSearchURLParams` 提取并监听 URL query 参数作为唯一数据源。而 `store` 被细分为控制 UI 的 `searchStore` 与独立处理帖子浮层数据的 `previewStore`。
- **全局预览浮层**: `src/widgets/thread-preview/`，响应 `previewStore` 的状态从而在任意页面顶部展示帖子快照阅读流。
- **主框架皮肤与顶栏**: 放置在 `src/widgets/layout/` 中。这些区块天然包裹在页面周围，属于高度复用的骨架级挂件。
- **论坛内容的承接者**: `src/entities/thread/`，任何跟帖子这三个字本身有关的数据形态、卡片样式、Tag 样式，全都被内聚在此处。

## 3. 相对路径引用的绝对禁令

为了遏制无限层级的 `../../../` 黑洞引发困扰，配置了严格的 `@` 解析钩子。跨层级调用时，**必须使用以下标准写法**：

```typescript
// ❌ 严禁出现此类跨域穿透写法
import { Button } from '../../../../shared/ui/Button';

// ✅ 正确规范写法
import { Button } from '@/shared/ui/Button';
import { Thread } from '@/entities/thread/types';
// ✅ 对于由 npm run gen:api 产生的类型文件，专用了强关联短标识
import { paths } from '@shared-types/openapi'; 
```
