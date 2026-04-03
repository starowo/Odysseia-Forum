# 📖 项目概览 (Project Overview)

Odysseia Forum Webpage 是一个基于 React 18 与 Vite 构建的现代化单页应用 (SPA)。它采用了 Feature-Sliced Design (FSD) 理念，致力于提供流畅、美观、响应式的全平台论坛阅读与搜索体验。

## 1. 核心特性

- **性能驱动**: 结合 Vite 的极速冷启动与打包能力，配合路由级别的懒加载 (Code Splitting)。
- **交互创新**: 引入多套深浅色主题，支持平滑的主题切换动画；附带增强搜索引导体验的“看板娘”系统。
- **类型安全**: 基于 Zod 与自动生成的 OpenAPI 类型规范，保证从后端接口到前端表单的端到端类型安全。
- **数据流健壮**: 通过 `@tanstack/react-query` 彻底接管服务端并发、重试、旧数据缓存合并等逻辑。

## 2. 环境构建与运行

| 维度 | 本开发环境 | 生产环境 |
| --- | --- | --- |
| **构建机制** | `npm run dev` 使用 Vite 本地开发服务器，包含 HMR 热替换 | `npm run build` 生成优化后的静态资源 |
| **访问地址** | `http://localhost:3000` | 部署后的正式域名，通过 Cloudflare 边缘分发 |
| **API 指向** | 根据 `.env` 中填写的 `VITE_API_URL` 决定 | 指向正式后端域名，如 `https://api.example.com/v1` |

### 2.1 本地开发指南

1. 安装依赖引擎 (推荐使用 `pnpm` 或 `npm`)：
   ```bash
   npm install
   ```
2. 配置环境变量：将 `.env.example` 复制一份命名为 `.env` 或者 `.env.development`，并调整后端的运行地址：
   ```env
   VITE_API_URL=http://localhost:10810/v1
   ```
3. 启动开发服务器：
   ```bash
   npm run dev
   ```
4. 打开浏览器访问 `http://localhost:3000` 即可开始调试。

### 2.2 打包发布

直接执行打包命令：
```bash
npm run build
```
执行完毕后，所有静态文件将会输出至 `dist/` 目录。你只需将其托管至任何静态服务容器（例如 Nginx, Cloudflare Pages, Vercel 等）并配置好 API 跨域即可。

## 3. 代码审查及提交规范

- 在向代码主库提交 PR 前，请确保在本地完整运行过 `npm run lint` 和 `npm run test` 以排查阻断性错误。
- 更多详尽的架构分层理念、状态管理或组件编写规范，请跳转至当前目录的 `core_architecture.md` 以及 `docs/development/` 进一步阅读。