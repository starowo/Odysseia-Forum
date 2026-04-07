import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { toast } from 'sonner';
import { useRefreshAuth } from '@/features/auth/hooks/useAuth';
import { LOGIN_REDIRECT_STORAGE_KEY, sanitizeInternalRedirect } from '@/shared/lib/navigationSafety';
import { OmicronLoader } from '@/shared/ui/loaders/OmicronLoader';

export function CallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const refreshAuth = useRefreshAuth();

  useEffect(() => {
    const error = searchParams.get('error');

    if (error) {
      toast.error('登录失败: ' + error);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
      return;
    }

    // Token is now extracted in App.tsx via hash
    // Just handle redirect restoration here
    const savedRedirect = sessionStorage.getItem(LOGIN_REDIRECT_STORAGE_KEY);
    const queryRedirect = searchParams.get('redirect');

    sessionStorage.removeItem(LOGIN_REDIRECT_STORAGE_KEY);

    const redirectPath = sanitizeInternalRedirect(savedRedirect || queryRedirect || '/');

    toast.success('登录成功！');

    setTimeout(() => {
      refreshAuth();
      navigate(redirectPath, { replace: true });
    }, 500);
  }, [searchParams, navigate, refreshAuth]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--od-bg)]">
      <div className="text-center">
        <OmicronLoader className="mx-auto mb-4 h-12 w-12" />
        <p className="text-lg text-[var(--od-text-primary)]">正在登录...</p>
        <p className="mt-2 text-sm text-[var(--od-text-secondary)]">请稍候</p>
      </div>
    </div>
  );
}
