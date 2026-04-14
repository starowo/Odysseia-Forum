import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useRefreshAuth } from '@/features/auth/hooks/useAuth';
import { showMascotToast } from '@/features/mascot/lib/mascotToast';
import { notifySuccess } from '@/shared/lib/notify';
import { LOGIN_REDIRECT_STORAGE_KEY, sanitizeInternalRedirect } from '@/shared/lib/navigationSafety';
import { OmicronLoader } from '@/shared/ui/loaders/OmicronLoader';

export function CallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const refreshAuth = useRefreshAuth();

  useEffect(() => {
    const error = searchParams.get('error');

    if (error) {
      showMascotToast({
        id: 'auth-callback-error',
        emotion: 'sad_apology',
        eyebrow: 'Login Interrupted',
        title: '这次登录没接上',
        message: 'Discord 登录流程中断了。先回到登录页，我陪你重新试一次。',
        actionLabel: '返回登录页',
        onAction: () => navigate('/login', { replace: true }),
        cancelLabel: '稍后再说',
        duration: 7000,
      });

      navigate('/login', { replace: true });
      return;
    }

    // Token is now extracted in App.tsx via hash
    // Just handle redirect restoration here
    const savedRedirect = sessionStorage.getItem(LOGIN_REDIRECT_STORAGE_KEY);
    const queryRedirect = searchParams.get('redirect');

    sessionStorage.removeItem(LOGIN_REDIRECT_STORAGE_KEY);

    const redirectPath = sanitizeInternalRedirect(savedRedirect || queryRedirect || '/');

    notifySuccess('登录成功，正在回到你刚刚的位置', { id: 'auth-callback-success' });

    setTimeout(() => {
      refreshAuth();
      navigate(redirectPath, { replace: true });
    }, 700);
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
