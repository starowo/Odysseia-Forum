# Odysseia Forum - 前端项目

基于 **React 18 + TypeScript + Vite** 构建的现代化 Discord 论坛搜索前端，配合后端搜索 API，在浏览器中提供贴近 Discord 体验的搜索与浏览界面。

> 上游仓库 / PR 说明可参考同目录下的
> [`PROJECT_OVERVIEW.md`](webpage/PROJECT_OVERVIEW.md:1)。

---

## 🚀 本地快速开始（开发环境）

在 `webpage` 目录下执行以下步骤：

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件（示例）：

```env
# 本地 / 测试后端地址
VITE_API_URL=http://localhost:10810/v1

# Discord 相关配置（如需联通真实 OAuth）
VITE_GUILD_ID=your_guild_id
VITE_CLIENT_ID=your_discord_client_id
```

> 说明：
> - 开发过程中，如果只想使用本地 Mock 数据，可以保持 `VITE_API_URL` 指向本地测试后端或任意地址；
> - 具体与后端的对接方式、生产环境变量示例可参考
>   [`PROJECT_OVERVIEW.md`](webpage/PROJECT_OVERVIEW.md:1)。

### 3. 启动开发服务器

```bash
npm run dev
```

默认访问地址：<http://localhost:3000>

---

## 📦 技术栈

### 核心框架

- **React 18** - UI 框架
- **TypeScript 5** - 类型安全
- **Vite 5** - 构建工具

### 状态管理

- **Zustand** - 客户端状态管理（搜索条件、UI 状态等）
- **TanStack Query** - 服务端状态管理（搜索结果、关注列表等）

### UI 与交互

- **Tailwind CSS** - 原子化 CSS，配合自定义 CSS 变量实现主题系统
- **Framer Motion**（可选）- 动画库
- **Lucide React** - 图标库
- **Sonner** - Toast 通知
- 自研布局组件（侧边栏、顶栏、统计栏等）

### 开发辅助

- **React Router v6** - 路由管理
- **Axios** - HTTP 客户端
- **date-fns** - 日期处理
- **ahooks** - React Hooks 辅助库
- **MSW (Mock Service Worker)** - 本地接口模拟（搜索、元数据、关注等）

---

## 📁 项目结构（简要）

> 更详细的结构说明参见
> [`PROJECT_STRUCTURE.md`](webpage/PROJECT_STRUCTURE.md:1)。

```bash
src/
├── app/                          # 应用入口
│   ├── App.tsx                   # 根组件（Provider、路由容器）
│   └── router.tsx                # 路由配置
│
├── pages/                        # 页面
│   ├── SearchPage/               # 搜索首页
│   ├── FollowsPage/              # 关注列表页
│   ├── SettingsPage/             # 设置页
│   ├── AboutPage/                # 关于 / 说明页（含彩蛋）
│   └── AuthPage/                 # 登录 / OAuth 回调
│
├── features/                     # 按业务拆分的功能模块
│   ├── auth/                     # 认证相关
│   ├── search/                   # 搜索逻辑与 API
│   ├── follows/                  # 关注相关 API
│   └── threads/                  # 帖子卡片等
│
├── components/                   # 复用组件
│   ├── layout/                   # 布局组件（侧边栏、主布局等）
│   ├── common/                   # 通用小组件（按钮、滚动条、懒加载图片等）
│   ├── icons/                    # 图标封装
│   └── DevNav.tsx               # 开发调试用导航
│
├── hooks/                        # 通用 Hooks（主题、设置、快捷键等）
│   ├── useTheme.ts
│   ├── useSettings.ts
│   └── useKeyboardShortcuts.ts
│
├── lib/                          # 工具与设置
│   └── settings.ts               # 用户设置持久化等
│
├── mocks/                        # MSW mock 定义
│   ├── browser.ts
│   ├── handlers.ts               # 各业务接口的 mock
│   └── data.ts                   # mock 数据
│
├── styles/                       # 样式
│   ├── globals.css               # 全局样式 & 主题变量
│   └── themes.ts                 # 主题配置（多套主题）
│
├── assets/                       # 静态资源（背景图 / banner / icon 等）
└── main.tsx                      # React 入口
```

---

## 🛠️ 常用命令

```bash
# 启动开发服务器（含 HMR）
npm run dev

# 构建生产版本（输出到 dist/）
npm run build

# 本地预览构建结果
npm run preview

# 代码检查
npm run lint

# 代码格式化
npm run format
```

---

## 🔧 配置与环境说明

### 环境变量

- `VITE_API_URL`：后端 API 基础地址（本地 / 测试 / 生产各不相同）
- `VITE_GUILD_ID`：Discord 服务器 ID（如需与真实服务器联动）
- `VITE_CLIENT_ID`：Discord OAuth 应用 Client ID

开发 / 测试 / 生产环境差异，以及在 Cloudflare 上的部署方式，见
[`PROJECT_OVERVIEW.md`](webpage/PROJECT_OVERVIEW.md:1)。

### Vite / TS / Tailwind

- 路径别名：`@` 指向 `src` 目录
- TypeScript 开启严格模式，使用路径映射与 ESNext 模块
- Tailwind 配合自定义 `--od-*` CSS 变量实现深浅色多主题，并支持平滑主题切换动画

---

## 📝 开发规范

### 代码风格

- 使用 **ESLint** 进行代码检查
- 使用 **Prettier** 进行代码格式化
- 遵循 React Hooks 规则，避免在条件语句中调用 Hook
- 尽量使用 TypeScript 类型约束组件 props 与函数返回值

### 命名规范

- 组件：`PascalCase`（如 `SearchBar.tsx`）
- 函数 / Hook：`camelCase`（如 `useSearchStore.ts`）
- 常量：`UPPER_SNAKE_CASE`（如 `API_URL`）

### Git 提交前缀建议

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 仅样式 / 格式调整
- `refactor`: 代码重构（无功能变更）
- `test`: 测试相关
- `chore`: 构建 / 工具 / 依赖调整

---

## ✅ 功能概览（当前进度）

- [x] 搜索页面布局与交互
- [x] 搜索筛选器组件（频道、标签、时间范围等）
- [x] 帖子卡片组件（含 skeleton、统计信息等）
- [x] 关注列表页面
- [x] Banner 轮播与推荐位
- [x] 标签系统与偏好设置
- [x] 多主题支持（深色 / 浅色 + 自定义主题）
- [ ] 虚拟滚动优化（大规模列表性能优化）
- [ ] 移动端进一步适配与优化

---

## 📄 许可证

MIT License
