# Odysseia Forum 新前端 - PR 说明

本文件用于配合提交到上游仓库的前端 PR，说明本地开发环境与实际生产环境（Cloudflare 部署）的差异，以及如何在不同环境下运行本项目。

## 1. 本 PR 概览

- 引入基于 React 18 + Vite 的单页应用前端
- 实现搜索页、关注页、设置页、关于页等核心页面布局
- 新增主题系统（多套深浅色主题 + 主题切换动画）
- 整合 Mock Service Worker（MSW）用于本地开发时的接口模拟
- 与现有后端接口契合的搜索 / 关注等数据结构

## 2. 环境对比：本地开发 vs 生产环境

| 维度 | 本地开发环境 | 生产环境 |
| --- | --- | --- |
| 前端构建 | `npm run dev` 使用 Vite 本地开发服务器 | `npm run build` 生成静态资源，部署到 Cloudflare Pages 等静态托管 |
| 访问地址 | `http://localhost:3000` | 例如 `https://forum.example.com`（由 Cloudflare 提供） |
| API 地址 | 由 `.env` / `.env.development` 中的 `VITE_API_URL` 决定，通常指向本地或测试后端 | 指向正式后端域名，例如 `https://api.example.com/v1` |
| 接口数据 | 默认启用 MSW，可模拟搜索、关注等接口返回 | 不启用 MSW，直接请求真实后端接口 |
| 静态资源 | 由 Vite 本地服务动态提供 | 由 Cloudflare 的边缘节点缓存并分发 |

> 说明：MSW 只用于本地 / 测试环境，构建线上生产版本时不会被打包进最终产物，也不会拦截真实请求。

## 3. 本地开发环境说明

1. 在 `webpage` 目录下安装依赖：

   ```bash
   npm install
   ```

2. 复制示例环境变量并根据需要修改：

   ```bash
   cp .env.example .env
   ```

3. 在 `.env` 中配置开发用后端地址（示例）：

   ```env
   VITE_API_URL=http://localhost:10810/v1
   VITE_GUILD_ID=your_guild_id
   VITE_CLIENT_ID=your_discord_client_id
   ```

4. 启动开发服务器：

   ```bash
   npm run dev
   ```

5. 打开浏览器访问 `http://localhost:3000`，即可使用带有模拟数据的前端界面进行开发和交互测试。

## 4. 生产部署（Cloudflare）说明

生产环境推荐流程：

1. 在构建环境中配置生产用环境变量（示例）：

   ```env
   VITE_API_URL=https://api.example.com/v1
   VITE_GUILD_ID=your_production_guild_id
   VITE_CLIENT_ID=your_production_client_id
   ```

2. 执行生产构建：

   ```bash
   npm run build
   ```

3. 将生成的 `dist/` 目录作为静态站点部署到 Cloudflare：

- 使用 Cloudflare Pages：
  - Build 命令：`npm run build`
  - Output 目录：`dist`
- 或其他 Cloudflare 静态托管方式，确保 `dist` 目录中的文件可直接通过 HTTPS 访问

4. 确认 Cloudflare 所在域名已正确指向后端 API 所在域名，满足 CORS 与鉴权等要求。

## 5. 与上游后端对接时的注意事项

- 若上游希望在本地复现前端效果，建议：
  - 按「本地开发环境说明」步骤运行
  - 如需连真实后端，可在 `.env` 中关闭 / 注释 MSW 相关初始化逻辑，或将 `VITE_API_URL` 指向其后端测试环境
- PR 中涉及的接口路径、参数和返回结构已按当前后端实现对齐，如后端有更新，可以在前端的 `features/*/api` 模块中协同调整。

## 6. 如何在 review 时快速验证

- 拉取 PR 对应分支：

  ```bash
  git checkout feature/new-frontend
  cd webpage
  npm install
  npm run dev
  ```

- 打开 `http://localhost:3000`，可主要验证：
  - 搜索页：搜索表单、过滤条件、结果列表、分页
  - 关注页：关注线程列表及骨架加载状态
  - 设置页：主题切换、偏好设置等
  - 关于页：项目信息与彩蛋效果