import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { DiscordIcon } from '@/components/icons/DiscordIcon';
import { useRefreshAuth } from '@/features/auth/hooks/useAuth';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import forumIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import backgroundImage from '@/assets/images/background/winter.png';

export function LoginPage() {
  const navigate = useNavigate();
  const refreshAuth = useRefreshAuth();

  const handleLogin = async () => {
    // 在 Mock 模式下，这将由 msw 拦截
    try {
      const response = await apiClient.post('/auth/login');
      if (response.data.token) {
        localStorage.setItem('auth_token', response.data.token);
        toast.success('登录成功！');
        refreshAuth();
        setTimeout(() => navigate('/', { replace: true }), 300);
      }
    } catch (error) {
      toast.error('登录失败，请稍后重试。');
      // 在真实环境中，这里应该跳转到 Discord OAuth 页面
      // const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:10810/v1';
      // window.location.href = `${apiUrl}/auth/login`;
    }
  };

  return (
    <div 
      className="flex min-h-screen items-center justify-center px-4 bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: `url(${backgroundImage})` }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-sm text-center bg-[#1e1f22]/80 backdrop-blur-lg rounded-3xl p-8 shadow-2xl"
      >
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <img 
            src={forumIcon} 
            alt="类脑ΟΔΥΣΣΕΙΑ" 
            className="h-24 w-24 rounded-3xl shadow-2xl"
          />
        </div>

        {/* 标题 */}
        <h1 className="mb-3 text-4xl font-bold text-[#f2f3f5]">类脑ΟΔΥΣΣΕΙΑ</h1>
        <p className="mb-12 text-[#b5bac1]">使用 Discord 登录以继续</p>

        {/* 登录按钮 */}
        <button
          onClick={handleLogin}
          className="w-full rounded-2xl bg-[#5865F2] px-8 py-5 font-semibold text-white shadow-lg shadow-[#5865F2]/50 transition-all hover:scale-105 hover:shadow-xl hover:shadow-[#5865F2]/60"
        >
          <div className="flex items-center justify-center gap-3">
            <DiscordIcon className="h-7 w-7" />
            <span className="text-lg">
              使用 Discord 登录
            </span>
          </div>
        </button>

        {/* 说明文字 */}
        <p className="mt-8 text-sm text-[#949ba4]">
          我们仅读取你的基本信息，不会发送任何消息
        </p>
      </motion.div>
    </div>
  );
}
