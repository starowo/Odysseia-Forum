import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth, useRefreshAuth } from '@/features/auth/hooks/useAuth';
import { consumeAuthTokenFromHash, hasAuthTokenInHash } from '@/shared/lib/authSession';
import { buildCurrentAppRedirect, LOGIN_REDIRECT_STORAGE_KEY } from '@/shared/lib/navigationSafety';
import { OmicronLoader } from '@/shared/ui/loaders/OmicronLoader';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const refreshAuth = useRefreshAuth();
  // 初始状态即检测是否有 Token 需要处理，防止首屏渲染直接触发重定向
  const [isProcessingToken, setIsProcessingToken] = useState(() => hasAuthTokenInHash());

  useEffect(() => {
    if (hasAuthTokenInHash()) {
      setIsProcessingToken(true);
      const token = consumeAuthTokenFromHash();

      if (token) {
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
    const currentPath = buildCurrentAppRedirect();
    sessionStorage.setItem(LOGIN_REDIRECT_STORAGE_KEY, currentPath);
    return <Navigate to={`/login?redirect=${encodeURIComponent(currentPath)}`} replace />;
  }

  // 已认证，显示内容
  return <Outlet />;
}
