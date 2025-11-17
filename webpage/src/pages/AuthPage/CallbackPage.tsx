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
    const token = searchParams.get('token');
    const error = searchParams.get('error');

    if (error) {
      toast.error('登录失败: ' + error);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
      return;
    }

    if (token) {
      // 保存token（虽然后端主要使用Cookie，但保存token以备用）
      localStorage.setItem('auth_token', token);
      
      toast.success('登录成功！');
      
      // 延迟跳转，确保Cookie已设置
      setTimeout(() => {
        // 刷新认证状态
        refreshAuth();
        navigate('/', { replace: true });
      }, 1000);
    } else {
      // 可能后端直接设置了Cookie，没有返回token
      // 尝试检查认证状态
      setTimeout(async () => {
        refreshAuth();
        navigate('/', { replace: true });
      }, 1000);
    }
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
