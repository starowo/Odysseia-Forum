# Cloudflare Pages 部署指南

## 概述
本文档说明如何将 Odysseia Forum 前端应用部署到 Cloudflare Pages。

## 前置要求
- Cloudflare 账号
- GitHub/GitLab 仓库访问权限
- 后端 API 已部署并可访问

## 部署步骤

### 1. 创建 Cloudflare Pages 项目

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Workers & Pages** > **Pages**
3. 点击 **Create a project** > **Connect to Git**
4. 选择你的 Git 仓库（GitHub 或 GitLab）
5. 授权 Cloudflare 访问仓库

### 2. 配置构建设置

在项目配置页面，设置以下参数：

#### 基本设置
- **项目名称**: `odysseia-forum-web`（或自定义）
- **生产分支**: `main`（或你的主分支）
- **根目录**: `/webpage`（重要！因为前端代码在 webpage 子目录）

#### 构建设置
- **框架预设**: `Vite`
- **构建命令**: `npm run build`
- **构建输出目录**: `dist`
- **Node.js 版本**: `18` 或更高

### 3. 环境变量配置

在 **Settings** > **Environment variables** 中添加：

| 变量名 | 示例值 | 说明 |
|--------|--------|------|
| `VITE_API_URL` | `https://api.odysseia.example.com/v1` | 后端 API 地址（必填） |
| `VITE_USE_MOCK` | `false` | 生产环境必须设为 `false` |
| `NODE_VERSION` | `18` | Node.js 版本 |

> **重要**: 环境变量必须以 `VITE_` 开头才能在前端代码中访问。

### 4. 部署

1. 点击 **Save and Deploy**
2. Cloudflare Pages 会自动：
   - 克隆仓库
   - 安装依赖（`npm install`）
   - 运行构建（`npm run build`）
   - 部署到 CDN

3. 等待构建完成（通常 2-5 分钟）

### 5. 验证部署

部署完成后，访问 Cloudflare 提供的域名（例如 `odysseia-forum-web.pages.dev`）：

#### 验证清单
- [ ] 页面能正常加载（无白屏）
- [ ] 刷新任意子路由（如 `/login`, `/follows`）不报 404
- [ ] 侧边栏显示频道列表
- [ ] 搜索功能正常
- [ ] 登录跳转正常（需确保后端 CORS 和回调 URL 配置正确）

## 关键配置文件

### `/webpage/public/_redirects`
```
/* /index.html 200
```
此文件确保所有路由请求都返回 `index.html`，实现 SPA 路由支持。**已自动包含在构建输出中**。

### `/webpage/src/config/channels.ts`
静态频道配置，作为 API 失败时的回退数据。如果后端 `/meta/channels` 不可用，前端会自动使用此配置。

## 常见问题 & 注意事项

### ❌ 刷新页面出现 404
**原因**: 缺少 `_redirects` 文件  
**解决**: 确认 `public/_redirects` 文件存在，并且构建后被复制到 `dist/` 目录

### ❌ 侧边栏频道列表为空
**可能原因**:
1. 后端 `/meta/channels` API 不可用
2. CORS 配置问题

**解决**:
1. 检查后端 API 是否正常
2. 检查后端 CORS 配置，确保允许前端域名
3. 前端已内置回退机制，API 失败会自动使用静态配置

### ❌ 登录后跳转失败
**原因**: 后端 `redirect_uri` 配置错误  
**解决**: 在后端 `config.json` 中设置：
```json
{
  "frontend_url": "https://your-domain.pages.dev",
  "redirect_uri": "https://your-domain.pages.dev/"
}
```

### ⚠️ API 请求失败 (CORS)
**解决**: 后端必须配置 CORS，允许前端域名：
```python
# 示例 FastAPI CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.pages.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### ⚠️ 环境变量不生效
**原因**: Vite 只在构建时读取环境变量  
**解决**: 修改环境变量后，必须重新触发部署（或手动 Retry deployment）

## 自动部署

Cloudflare Pages 支持 Git 分支自动部署：

- **生产环境**: `main` 分支的 push 会自动触发生产部署
- **预览环境**: Pull Request 会自动创建预览部署，便于测试

## 自定义域名

1. 在 Cloudflare Pages 项目中，进入 **Custom domains**
2. 点击 **Set up a custom domain**
3. 输入你的域名（如 `forum.odysseia.com`）
4. 按照提示添加 DNS 记录（CNAME）

## 性能优化建议

- **启用 Cloudflare CDN**: 自动启用，全球加速
- **压缩**: 已自动启用 Brotli/Gzip 压缩
- **缓存**: 静态资源自动缓存在 Cloudflare 边缘节点
- **构建优化**: 当前 bundle 大小约 680 KB（已压缩到 206 KB），在合理范围内

## 回滚部署

如果新版本有问题：

1. 进入 **Deployments** 页面
2. 找到之前的稳定版本
3. 点击 **...** > **Rollback to this deployment**

## 技术支持

如遇到部署问题，请检查：
1. Cloudflare Pages 构建日志
2. 浏览器开发者工具的控制台和网络面板
3. 后端 API 日志

---

**最后更新**: 2025-11-25  
**文档版本**: 1.0
