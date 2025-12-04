import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useRefreshAuth } from '@/features/auth/hooks/useAuth';

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
    const savedRedirect = sessionStorage.getItem('login_redirect');
    const queryRedirect = searchParams.get('redirect');

    sessionStorage.removeItem('login_redirect');

    const targetUrl = savedRedirect || queryRedirect || '/';

    // Extract path from full URL if needed
    let redirectPath = targetUrl;
    try {
      const url = new URL(targetUrl);
      redirectPath = url.pathname + url.search + url.hash;
    } catch {
      // targetUrl is already a path
    }

    toast.success('登录成功！');

    setTimeout(() => {
      refreshAuth();
      navigate(redirectPath, { replace: true });
    }, 500);
  }, [searchParams, navigate, refreshAuth]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--od-bg)]">
      <div className="text-center">
        <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-[var(--od-accent)]" />
        <p className="text-lg text-[var(--od-text-primary)]">正在登录...</p>
        <p className="mt-2 text-sm text-[var(--od-text-secondary)]">请稍候</p>
      </div>
    </div>
  );
}
