#!/usr/bin/env python3
"""简易静态文件服务器 for Odysseia Forum 网页前端"""

import http.server
import socketserver
import sys
from pathlib import Path

# 配置
PORT = 3000
DIRECTORY = Path(__file__).parent


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """支持CORS的请求处理器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        """添加CORS头"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        """处理预检请求"""
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        """自定义日志格式"""
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")


def main():
    """启动服务器"""
    handler = CORSRequestHandler

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print("🌐 Odysseia Forum 网页前端服务器")
        print(f"📂 服务目录: {DIRECTORY}")
        print(f"🚀 访问地址: http://localhost:{PORT}")
        print("⚠️  请确保在 config.json 中设置:")
        print(f"   frontend_url = http://localhost:{PORT}")
        print("   redirect_uri = http://localhost:8000/v1/auth/callback")
        print("\n按 Ctrl+C 停止服务器\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 服务器已停止")
            sys.exit(0)


if __name__ == "__main__":
    main()
