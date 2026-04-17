import { useEffect, useState, type CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { DiscordIcon } from '@/shared/ui/icons/DiscordIcon';
import { useAuth, useRefreshAuth } from '@/features/auth/hooks/useAuth';
import { apiClient } from '@/shared/api/client';
import forumIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import { showMascotToast } from '@/features/mascot/lib/mascotToast';
import { notifySuccess } from '@/shared/lib/notify';
import { WordLogoStatic } from '@/shared/ui/loaders/WordLogoStatic';
import backgroundImage from '@/assets/images/background/spring2.png';
import { WordLoader } from '@/shared/ui/loaders/WordLoader';

export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const refreshAuth = useRefreshAuth();
  const [isRedirecting, setIsRedirecting] = useState(false);
  const loadingWordStyle: CSSProperties & { '--od-text-primary': string } = {
    '--od-text-primary': 'color-mix(in oklab, var(--od-accent) 78%, white 22%)',
  };

  // 如果已经登录，自动跳转到首页
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleLogin = async () => {
    setIsRedirecting(true);

    // 在 Mock 模式下，这将由 msw 拦截
    if (import.meta.env.MODE === 'development' && import.meta.env.VITE_USE_MOCK === 'true') {
      setTimeout(async () => {
        try {
          const response = await apiClient.post('/auth/login');
          if (response.data.token) {
            localStorage.setItem('auth_token', response.data.token);
            notifySuccess('登录成功，欢迎回来', { id: 'login-mock-success' });
            refreshAuth();
            navigate('/', { replace: true });
          }
        } catch {
          showMascotToast({
            id: 'login-mock-error',
            emotion: 'error',
            eyebrow: 'Connection Failed',
            title: '登录入口没有接通',
            message: '刚才这次连接没成功。你可以立刻再试一次，我会继续盯着。',
            actionLabel: '重新登录',
            onAction: () => window.location.reload(),
            cancelLabel: '先停一下',
            onCancel: () => setIsRedirecting(false),
            duration: 7000,
          });
          setIsRedirecting(false);
        }
      }, 1500); // 留出 1.5s 播放 SVG 动画
      return;
    }

    // 真实环境：跳转到后端 OAuth 登录接口
    const loginPath = '/auth/login';
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'https://forum.shimmerday.top';
    const finalUrl = `${backendUrl}/v1${loginPath}`;
      
    setTimeout(() => {
      window.location.href = finalUrl;
    }, 1500); // 留出 1.5s 给动画绽放的时间
  };

  return (
    <div
      className="relative flex min-h-screen items-center overflow-hidden bg-cover bg-center bg-no-repeat px-4"
      style={{ backgroundImage: `url(${backgroundImage})` }}
    >
      {/* 登录等待时轻度压暗背景，保证动画可读性 */}
      <AnimatePresence>
        {isRedirecting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="absolute inset-0 z-0 bg-black/58 backdrop-blur-sm"
          />
        )}
      </AnimatePresence>

      <div
        className={`relative z-10 mx-auto flex w-full max-w-7xl ${
          isRedirecting ? 'justify-center' : 'justify-center md:justify-start md:pl-[8%] lg:pl-[10%]'
        }`}
      >
        <AnimatePresence mode="wait">
          {!isRedirecting ? (
            <motion.div
            key="login-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, filter: 'blur(8px)' }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="w-full max-w-sm rounded-3xl bg-[color-mix(in_oklab,var(--od-bg-tertiary)_85%,transparent)] p-8 text-center shadow-2xl backdrop-blur-lg"
          >
            {/* Logo */}
            <div className="mb-8 flex justify-center">
              <img
                src={forumIcon}
                alt="类脑ΟΔΥΣΣΕΙΑ"
                className="h-24 w-24 rounded-3xl shadow-2xl"
              />
            </div>

            {/* 标题：将普通文字升级为 SVG 图形标题 */}
            <div className="flex flex-col items-center justify-center mb-10 gap-2 max-w-full overflow-hidden">
              <span className="text-xl font-bold tracking-[0.2em] text-[var(--od-text-primary)]">类脑</span>
              <WordLogoStatic className="h-5 shrink-0 text-[var(--od-text-primary)] sm:h-6" />
            </div>

            <p className="mb-10 text-[var(--od-text-secondary)]">使用 Discord 登录以继续</p>

            {/* 登录按钮 */}
            <button
              onClick={handleLogin}
              className="w-full rounded-2xl bg-[var(--od-accent)] px-8 py-5 font-semibold text-white shadow-lg transition-all hover:scale-105 hover:shadow-xl"
            >
              <div className="flex items-center justify-center gap-3">
                <DiscordIcon className="h-7 w-7" />
                <span className="text-lg">
                  使用 Discord 登录
                </span>
              </div>
            </button>

            {/* 说明文字 */}
            <p className="mt-8 text-sm text-[var(--od-text-tertiary)]">
              我们仅读取你的基本信息，不会发送任何消息
            </p>
          </motion.div>
        ) : (
          <motion.div
            key="loading-animation"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.1 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="flex flex-col items-center justify-center"
            style={loadingWordStyle}
          >
            <div className="flex scale-100 items-center justify-center sm:scale-110 md:scale-125 drop-shadow-[0_0_20px_rgba(255,255,255,0.25)]">
              <WordLoader />
            </div>
            <motion.p 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="mt-12 animate-pulse text-base font-semibold tracking-[0.2em] text-[var(--od-text-primary)]"
            >
              INITIALIZING CONNECTION...
            </motion.p>
          </motion.div>
        )}
        </AnimatePresence>
      </div>
    </div>
  );
}
