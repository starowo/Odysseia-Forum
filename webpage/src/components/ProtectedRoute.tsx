import { Navigate, Outlet } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/features/auth/hooks/useAuth';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  // 显示加载界面直到认证检查完成
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--od-bg)]">
        <div className="text-center">
          <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-[var(--od-accent)]" />
          <p className="text-sm text-[var(--od-text-secondary)]">验证登录状态...</p>
        </div>
      </div>
    );
  }

  // 如果未认证，跳转到登录页
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // 已认证，显示内容
  return <Outlet />;
}
