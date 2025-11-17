#!/bin/bash

# 连接到服务器的快速配置脚本

echo "🔌 Odysseia Forum - 服务器连接配置"
echo "======================================"
echo ""

# 读取配置
read -p "请输入服务器 API 地址 (例如: https://api.example.com/v1): " API_URL
read -p "请输入 Discord Guild ID: " GUILD_ID
read -p "请输入 Discord Client ID: " CLIENT_ID

# 确认
echo ""
echo "配置信息："
echo "  API 地址: $API_URL"
echo "  Guild ID: $GUILD_ID"
echo "  Client ID: $CLIENT_ID"
echo ""
read -p "确认配置正确？(y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "已取消配置"
    exit 1
fi

# 创建 .env 文件
cat > .env << EOF
# API Configuration
VITE_API_URL=$API_URL
VITE_GUILD_ID=$GUILD_ID
VITE_CLIENT_ID=$CLIENT_ID

# Development Mode (连接真实后端)
VITE_USE_MOCK_AUTH=false

# Show TanStack Query DevTools
VITE_SHOW_DEVTOOLS=false
EOF

echo ""
echo "✅ 配置完成！"
echo ""
echo "下一步："
echo "1. 确保服务器上的 Bot 正在运行"
echo "2. 在 Discord Developer Portal 配置 OAuth 回调地址"
echo "3. 运行 'npm run dev' 启动前端"
echo ""
echo "测试连接："
echo "  curl $API_URL/../health"
echo ""
