import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth, useRefreshAuth } from '@/features/auth/hooks/useAuth';
import { OmicronLoader } from '@/shared/ui/loaders/OmicronLoader';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const refreshAuth = useRefreshAuth();
  // 初始状态即检测是否有 Token 需要处理，防止首屏渲染直接触发重定向
  const [isProcessingToken, setIsProcessingToken] = useState(() => 
    window.location.hash.includes('token=')
  );

  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.includes('token=')) {
      setIsProcessingToken(true);
      // 使用正则匹配更准确
      const match = hash.match(/[#&]token=([^&]+)/);
      const token = match ? match[1] : null;

      if (token) {
        localStorage.setItem('auth_token', token);
        // 清除 URL hash
        window.history.replaceState(null, '', window.location.pathname);
        // 刷新认证状态
        refreshAuth();
      }

      // 给一点时间让状态更新
      setTimeout(() => setIsProcessingToken(false), 800);
    }
  }, [refreshAuth]);

  // 显示加载界面直到认证检查完成或正在处理 Token
  if (isLoading || isProcessingToken) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--od-bg)]">
        <div className="text-center">
          <OmicronLoader className="mx-auto mb-4 h-12 w-12" />
          <p className="text-sm text-[var(--od-text-secondary)]">验证登录状态...</p>
        </div>
      </div>
    );
  }

  // If not authenticated, save redirect URL and navigate to login
  if (!isAuthenticated) {
    const currentUrl = window.location.href;
    sessionStorage.setItem('login_redirect', currentUrl);
    return <Navigate to={`/login?redirect=${encodeURIComponent(currentUrl)}`} replace />;
  }

  // 已认证，显示内容
  return <Outlet />;
}
