import { Bookmark, Settings, Info, LogOut, Search as SearchIcon, Bell, Tag as TagIcon, TestTube } from 'lucide-react';
import ServerIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ThemeToggle } from '@/components/common/ThemeToggle';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useSearchStore } from '@/features/search/store/searchStore';
import { NotificationCenter } from '@/features/notifications/components/NotificationCenter';
import { apiClient } from '@/lib/api/client';
import type { Channel } from '@/types/thread.types';
import { AnimatedIcon } from '@/components/ui/animation/AnimatedIcon';

export function AppSidebar() {
  const { user } = useAuth();
  const location = useLocation();
  const { selectedChannel, setChannel } = useSearchStore();
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [hasUnreadNotifications, setHasUnreadNotifications] = useState(false);

  // 频道列表：在搜索页左侧展示（生产环境走真实 API，本地走 MSW mock）
  // 后端 /v1/meta/channels 返回的是扁平的 Channel[] 列表
  const { data: channels } = useQuery({
    queryKey: ['meta', 'channels'],
    queryFn: async () => {
      try {
        const res = await apiClient.get<Channel[]>('/meta/channels');
        // 如果 API 返回空数组（可能后端没配置），也使用 fallback
        if (!res.data || res.data.length === 0) {
          console.warn('API returned empty channels, using fallback config');
          const { FALLBACK_CHANNELS } = await import('@/config/channels');
          return FALLBACK_CHANNELS;
        }
        return res.data;
      } catch (error) {
        console.warn('Failed to fetch channels from API, using fallback config', error);
        const { FALLBACK_CHANNELS } = await import('@/config/channels');
        return FALLBACK_CHANNELS;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1, // 失败后只重试一次，尽快切换到 fallback
  });

  const handleLogout = async () => {
    try {
      // Import authApi at the top if needed
      const { authApi } = await import('@/features/auth/api/authApi');
      await authApi.logout();
    } catch (error) {
      console.error('Backend logout failed:', error);
    }
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
  };

  const handleNotificationUnreadChange = (count: number) => {
    setHasUnreadNotifications(count > 0);
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="flex h-full flex-col bg-[var(--od-bg-secondary)]">
      {/* 顶部 Header */}
      {/* 顶部 Header */}
      <div className="flex items-center gap-3 px-4 py-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center overflow-hidden rounded-full shadow-md">
          <img src={ServerIcon} alt="Server Icon" className="h-full w-full object-cover" />
        </div>
        <h1 className="text-lg font-bold tracking-tight text-[var(--od-text-primary)]">
          类脑ΟΔΥΣΣΕΙΑ
        </h1>
      </div>

      {/* 滚动区域 */}
      <div className="flex-1 overflow-y-auto px-3 py-2 scrollbar-hide">
        {/* 频道列表 - 全局显示 */}
        <div className="mb-6">
          <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
            频道
          </div>

          <div className="space-y-0.5">
            {/* 全频道 */}
            <button
              onClick={() => setChannel(null)}
              className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${!selectedChannel
                ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)] font-medium'
                : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${!selectedChannel ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-text-tertiary)]'}`} />
              <span>全频道</span>
            </button>

            {/* 动态频道列表 */}
            {channels?.map((ch) => {
              const active = selectedChannel === ch.id;
              return (
                <button
                  key={ch.id}
                  onClick={() => setChannel(ch.id)}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${active
                    ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)] font-medium'
                    : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                    }`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-text-tertiary)]'}`} />
                  <span className="truncate">{ch.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 快捷操作 */}
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between px-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
              快捷操作
            </h2>
            <ThemeToggle />
          </div>
          <div className="space-y-0.5">
            <Link
              to="/"
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${isActive('/')
                ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)]'
                : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
            >
              <AnimatedIcon
                icon={SearchIcon}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/') ? 'text-[var(--od-accent)]' : ''}`}
                animation="scale"
                trigger="hover"
              />
              <span className="truncate">搜索页面</span>
            </Link>

            <button
              type="button"
              onClick={() => setNotificationOpen((prev) => !prev)}
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${notificationOpen
                ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)]'
                : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
            >
              <span className="relative inline-flex">
                <AnimatedIcon
                  icon={Bell}
                  className={`h-4 w-4 flex-shrink-0 ${notificationOpen ? 'text-[var(--od-accent)]' : ''
                    } ${hasUnreadNotifications ? 'notification-bell-wiggle' : ''}`}
                  animation="shake"
                  trigger="hover"
                />
                {hasUnreadNotifications && (
                  <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-[var(--od-error)] shadow-[0_0_0_2px_var(--od-bg)]" />
                )}
              </span>
              <span className="truncate">通知中心</span>
            </button>

            <Link
              to="/follows"
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${isActive('/follows')
                ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)]'
                : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
            >
              <AnimatedIcon
                icon={Bookmark}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/follows') ? 'text-[var(--od-accent)]' : ''}`}
                animation="scale"
                trigger="hover"
              />
              <span className="truncate">我的关注</span>
            </Link>
            <Link
              to="/tags"
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${isActive('/tags')
                ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)]'
                : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
            >
              <AnimatedIcon
                icon={TagIcon}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/tags') ? 'text-[var(--od-accent)]' : ''}`}
                animation="rotate"
                trigger="hover"
              />
              <span className="truncate">标签总览</span>
            </Link>
            <Link
              to="/settings"
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${isActive('/settings')
                ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)]'
                : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
            >
              <AnimatedIcon
                icon={Settings}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/settings') ? 'text-[var(--od-accent)]' : ''}`}
                animation="spin"
                trigger="hover"
              />
              <span className="truncate">设置</span>
            </Link>
            <Link
              to="/about"
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${isActive('/about')
                ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)]'
                : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
            >
              <AnimatedIcon
                icon={Info}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/about') ? 'text-[var(--od-accent)]' : ''}`}
                animation="bounce"
                trigger="hover"
              />
              <span className="truncate">关于我们</span>
            </Link>

            {/* Dev Mode - Only visible in Mock environment */}
            {import.meta.env.VITE_API_MOCKING === 'true' && (
              <Link
                to="/test"
                className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${isActive('/test')
                  ? 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-primary)]'
                  : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                  }`}
              >
                <AnimatedIcon
                  icon={TestTube}
                  className={`h-4 w-4 flex-shrink-0 ${isActive('/test') ? 'text-[var(--od-accent)]' : ''}`}
                  animation="pulse"
                  trigger="hover"
                />
                <span className="truncate">开发者模式</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* 底部用户信息栏 */}
      <div className="border-t border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-3">
        <div className="flex items-center justify-between rounded-xl bg-[var(--od-bg-tertiary)] p-3 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="relative h-10 w-10 flex-shrink-0">
              <img
                src={user?.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : 'https://cdn.discordapp.com/embed/avatars/0.png'}
                alt={user?.username}
                className="h-full w-full rounded-full object-cover ring-2 ring-[var(--od-bg-secondary)]"
              />
              <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-[var(--od-bg-secondary)] bg-green-500" />
            </div>
            <div className="flex flex-col overflow-hidden">
              <span className="truncate text-sm font-bold text-[var(--od-text-primary)]">
                {user?.global_name || user?.username || 'Guest'}
              </span>
              <span className="truncate text-xs text-[var(--od-text-tertiary)]">
                @{user?.username}
              </span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="rounded-lg p-2 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-error)]"
            title="登出"
          >
            <AnimatedIcon icon={LogOut} className="h-5 w-5" animation="shake" trigger="hover" />
          </button>
        </div>
      </div>

      {/* 通知中心面板 */}
      <NotificationCenter
        open={notificationOpen}
        onClose={() => setNotificationOpen(false)}
        onUnreadChange={handleNotificationUnreadChange}
      />
    </div>
  );
}
