# Odysseia Forum 网页前端

简易静态文件服务器，用于本地开发和测试。

## 快速开始

### Windows 用户

双击 `start.bat` 即可启动服务器。

### 所有平台

```bash
cd webpage
python server.py
```

服务器将在 `http://localhost:3000` 启动。

## 配置说明

启动前端服务器后，需要在 `config.json` 中配置以下内容：

```json
{
  "auth": {
    "frontend_url": "http://localhost:3000",
    "redirect_uri": "http://localhost:8000/v1/auth/callback"
  }
}
```

### Discord 开发者后台配置

1. 访问 https://discord.com/developers/applications
2. 选择你的应用
3. 进入 **OAuth2** → **Redirects**
4. 添加重定向URL：`http://localhost:8000/v1/auth/callback`
5. 保存更改

## 服务器特性

- ✅ 自动CORS支持
- ✅ 禁用缓存（便于开发）
- ✅ 简洁的日志输出
- ✅ 支持所有静态文件类型

## 端口说明

- **前端服务器**: `http://localhost:3000` （此服务器）
- **后端API**: `http://localhost:8000` （FastAPI服务）

## 故障排查

### 端口被占用

如果3000端口被占用，编辑 `server.py` 修改 `PORT` 变量：

```python
PORT = 3001  # 或其他可用端口
```

然后同步更新 `config.json` 中的 `frontend_url`。

### OAuth 登录失败

确保：
1. ✅ 前端服务器正在运行
2. ✅ 后端API正在运行
3. ✅ `config.json` 配置正确
4. ✅ Discord开发者后台的redirect_uri完全匹配

## 生产部署

生产环境建议使用专业的Web服务器：
- **Nginx** - 推荐用于生产环境
- **Caddy** - 自动HTTPS
- **Cloudflare Pages** - 免费CDN和静态托管

参考 `src/webpage/README.md` 了解如何部署到Cloudflare Pages。