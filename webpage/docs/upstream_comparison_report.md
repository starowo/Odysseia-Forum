# 前端差异对比与改进报告

## 1. 概述
本报告对比了 `upstream/main` (参考前端) 与当前 `feature/new-frontend` (React 前端) 在 **用户头像** 和 **认证流程** 方面的实现差异，并提出了相应的改进建议。

## 2. 头像功能 (Avatar)

### 现状对比
-   **Upstream (参考)**:
    -   后端在帖子数据中返回 `author` 对象，包含 `id`, `avatar` (hash), `username` 等字段。
    -   前端通过 Discord CDN 构建头像 URL: `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`。
    -   如果无头像，使用默认头像。
-   **Local (当前)**:
    -   `ThreadCard` 组件仅显示作者名称 (`display_name` / `global_name`)。
    -   `Thread` 类型定义可能缺少 `avatar` 字段（需确认）。
    -   界面上没有预留头像显示位置。

### 改进建议
1.  **更新类型定义**: 确保 `Thread` 接口中的 `author` 字段包含 `id` 和 `avatar`。
2.  **工具函数**: 添加 `getAvatarUrl(user)` 工具函数，复用 Discord CDN 构建逻辑。
3.  **UI 更新**: 修改 `ThreadCard` 组件，在作者名称旁添加圆形头像。

## 3. 认证流程 (Authentication)

### 现状对比
-   **Upstream (参考)**:
    -   **登录**: 点击登录按钮直接跳转到后端 OAuth 端点 `${AUTH_URL}/auth/login`。
    -   **回调**: 登录成功后，后端重定向回前端，并在 URL Hash 中携带 Token (例如 `#token=...`)。
    -   **Token 处理**: 前端在初始化时 (`init()`) 检查 URL Hash，提取 Token 并存入 `localStorage`。
    -   **请求**: 所有 API 请求在 Header 中携带 `Authorization: Bearer ${token}`。
-   **Local (当前)**:
    -   **登录**: `LoginPage` 使用 `apiClient.post('/auth/login')`。这在 Mock 环境下有效，但在真实环境下是错误的（真实环境需要 OAuth 跳转）。
    -   **Token 处理**: `client.ts` 已配置拦截器，能自动从 `localStorage` 读取 Token 并添加到 Header。
    -   **回调**: 缺少处理 URL Hash 中 Token 的逻辑。

### 改进建议
1.  **修改登录逻辑**: 将 `LoginPage` 的登录行为改为直接跳转到 `import.meta.env.VITE_API_URL + '/auth/login'`。
2.  **添加回调处理**:
    -   在 `App.tsx` 或 `AuthProvider` 中添加初始化逻辑。
    -   检查 `window.location.hash` 是否包含 `token`。
    -   如果包含，提取并存入 `localStorage`，然后清除 Hash。
3.  **环境变量**: 确保 `VITE_API_URL` 在生产环境配置正确。

## 4. API 接口兼容性分析

### 发现的问题
通过对比本地前端 (`webpage/src`)、上游前端 (`webpage_reference`) 和后端 (`src/api`)，发现以下不兼容之处：

#### 1. 认证 (Auth)
-   **登录**: 本地前端调用 `POST /auth/login`，但后端仅提供 `GET /auth/login` (用于 OAuth 重定向)。
-   **登出**: 本地前端调用 `POST /auth/logout`，但后端仅提供 `GET /auth/logout`。

#### 2. 标签 (Tags)
-   **获取标签**: 本地前端 `searchApi.ts` 尝试调用 `GET /tags`，但后端**不存在此接口**。
-   **正确做法**: 上游前端通过 `/search` 接口的响应 (`available_tags` 字段) 获取当前上下文的可用标签。
-   **Meta 路由**: 后端定义了 `meta` 路由 (`/meta/channels`)，但似乎未在 `src/api/main.py` 中注册，导致无法访问。

#### 3. 缺失功能
-   **Banner 申请**: 本地前端缺少 Banner 申请功能 (后端有 `POST /banner/apply`)。
-   **图片刷新**: 本地前端缺少图片刷新功能 (后端有 `POST /fetch-images`)。

### 修复建议
1.  **Auth**: 修正 `authApi.ts` 和 `LoginPage`，使用正确的 GET 请求进行跳转和登出。
2.  **Tags**:
    -   修改 `searchApi.ts`，移除 `getAvailableTags` 的独立调用。
    -   更新 Search Store，从 `/search` 响应中提取并更新可用标签。
3.  **Meta**: 如果需要独立获取频道/标签信息，需要在 `src/api/main.py` 中注册 `meta` 路由。
4.  **功能补全**: 后续计划中应补充 Banner 和 Fetch Images 的前端实现。

## 5. 实施计划 (更新)

1.  **类型与工具**:
    -   更新 `src/types/thread.types.ts` (添加 avatar, 修正 search response)。
    -   创建 `src/lib/utils/discord.ts`。
2.  **组件更新**:
    -   修改 `ThreadCard.tsx` 显示头像。
3.  **认证改造**:
    -   修改 `LoginPage.tsx` (OAuth 跳转)。
    -   修改 `authApi.ts` (Logout 改为 GET 或直接清除本地状态)。
    -   添加 Hash 回调处理。
4.  **API 修复**:
    -   修改 `searchApi.ts`，移除 `/tags` 调用。
    -   修改 `searchStore.ts`，从搜索结果更新标签。
