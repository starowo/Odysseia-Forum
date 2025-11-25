import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth, useRefreshAuth } from '@/features/auth/hooks/useAuth';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const refreshAuth = useRefreshAuth();
  const [isProcessingToken, setIsProcessingToken] = useState(false);

  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.includes('token=')) {
      setIsProcessingToken(true);
      const params = new URLSearchParams(hash.substring(1)); // remove #
      const token = params.get('token');

      if (token) {
        localStorage.setItem('auth_token', token);
        // 清除 URL hash
        window.history.replaceState(null, '', window.location.pathname);
        // 刷新认证状态
        refreshAuth();
      }

      // 给一点时间让状态更新
      setTimeout(() => setIsProcessingToken(false), 500);
    }
  }, [refreshAuth]);

  // 显示加载界面直到认证检查完成或正在处理 Token
  if (isLoading || isProcessingToken) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--od-bg)]">
        <div className="text-center">
          <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-[var(--od-accent)]" />
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
