import { useEffect, useState } from 'react';
import { isDevelopmentMode } from '@/lib/mockAuth';

export function TestPage() {
  const [info, setInfo] = useState({
    isDev: false,
    hasToken: false,
    token: '',
    mockUser: '',
  });

  useEffect(() => {
    setInfo({
      isDev: isDevelopmentMode(),
      hasToken: !!localStorage.getItem('auth_token'),
      token: localStorage.getItem('auth_token') || 'none',
      mockUser: localStorage.getItem('mock_user') || 'none',
    });
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-white">
      <h1 className="mb-8 text-3xl font-bold">开发模式测试页面</h1>
      
      <div className="space-y-4 rounded-lg bg-slate-900 p-6">
        <div>
          <strong>开发模式:</strong> {info.isDev ? '✅ 已启用' : '❌ 未启用'}
        </div>
        <div>
          <strong>有 Token:</strong> {info.hasToken ? '✅ 是' : '❌ 否'}
        </div>
        <div>
          <strong>Token 值:</strong>
          <pre className="mt-2 rounded bg-slate-800 p-2 text-xs">{info.token}</pre>
        </div>
        <div>
          <strong>Mock User:</strong>
          <pre className="mt-2 rounded bg-slate-800 p-2 text-xs">{info.mockUser}</pre>
        </div>
      </div>

      <div className="mt-8 space-x-4">
        <button
          onClick={() => {
            localStorage.clear();
            window.location.reload();
          }}
          className="rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600"
        >
          清除 LocalStorage
        </button>
        <button
          onClick={() => window.location.reload()}
          className="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
        >
          刷新页面
        </button>
      </div>
    </div>
  );
}
