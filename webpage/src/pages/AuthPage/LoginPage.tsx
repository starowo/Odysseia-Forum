import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { DiscordIcon } from '@/components/icons/DiscordIcon';
import { mockAuthApi, isDevelopmentMode } from '@/lib/mockAuth';
import { useRefreshAuth } from '@/features/auth/hooks/useAuth';
import { toast } from 'sonner';
import forumIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import backgroundImage from '@/assets/images/background/winter.png';

export function LoginPage() {
  const navigate = useNavigate();
  const refreshAuth = useRefreshAuth();

  const handleLogin = async () => {
    // 开发模式：使用模拟登录
    if (isDevelopmentMode()) {
      await mockAuthApi.login();
      toast.success('模拟登录成功！');
      
      // 刷新认证状态
      refreshAuth();
      
      // 延迟跳转，确保状态已更新
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 300);
      return;
    }

    // 生产模式：跳转到真实的 Discord OAuth
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:10810/v1';
    window.location.href = `${apiUrl}/auth/login`;
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
              {isDevelopmentMode() ? '模拟登录（开发模式）' : '使用 Discord 登录'}
            </span>
          </div>
        </button>

        {/* 说明文字 */}
        <p className="mt-8 text-sm text-[#949ba4]">
          {isDevelopmentMode() 
            ? '开发模式：点击按钮直接进入系统，无需真实登录'
            : '我们仅读取你的基本信息，不会发送任何消息'
          }
        </p>
      </motion.div>
    </div>
  );
}
