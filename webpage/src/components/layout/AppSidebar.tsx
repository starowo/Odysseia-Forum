import { Globe, Bookmark, Settings, Info, LogOut, Search as SearchIcon, Bell } from 'lucide-react';
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { UserCard } from '@/components/layout/UserCard';
import { ThemeToggle } from '@/components/common/ThemeToggle';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useSearchStore } from '@/features/search/store/searchStore';
import { NotificationCenter } from '@/features/notifications/components/NotificationCenter';
import { apiClient } from '@/lib/api/client';
import type { Channel } from '@/types/thread.types';

export function AppSidebar() {
  const { user } = useAuth();
  const location = useLocation();
  const { selectedChannel, setChannel } = useSearchStore();
  const isSearchPage = location.pathname === '/';
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [hasUnreadNotifications, setHasUnreadNotifications] = useState(false);

  // 频道列表：在搜索页左侧展示（生产环境走真实 API，本地走 MSW mock）
  // 后端 /v1/meta/channels 返回的是扁平的 Channel[] 列表
  const { data: channels } = useQuery({
    queryKey: ['meta', 'channels'],
    queryFn: async () => {
      const res = await apiClient.get<Channel[]>('/meta/channels');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const handleLogout = () => {
    try {
      localStorage.removeItem('auth_token');
    } catch (error) {
      console.error('Failed to clear auth token on logout:', error);
    }
    window.location.href = '/login';
  };

  const handleNotificationUnreadChange = (count: number) => {
    setHasUnreadNotifications(count > 0);
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="flex h-full flex-col">
      {/* 用户信息卡片 */}
      <UserCard
        username={user?.username || user?.global_name || 'Discord User'}
        avatar={user?.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : undefined}
        status="online"
      />

      {/* 分隔线 */}
      <div className="my-2 h-px bg-[var(--od-border-strong)]" />

      {/* 频道（仅在搜索页显示） */}
      {isSearchPage && (
        <>
          {/* 频道区：在从其他页面切回搜索页时做一个轻微滑入 + 淡入 */}
          <div className="mb-6 animate-in fade-in slide-in-from-top-2 duration-300">
            <h2 className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
              频道
            </h2>
            <div className="space-y-0.5">
              {/* 全频道 */}
              <button
                onClick={() => setChannel(null)}
                className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
                  !selectedChannel
                    ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                    : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
                }`}
              >
                <Globe
                  className={`h-4 w-4 flex-shrink-0 ${
                    !selectedChannel ? 'text-[var(--od-accent)]' : ''
                  }`}
                />
                <span className="truncate">全频道</span>
              </button>
            </div>

            {/* 具体频道列表（从 /meta/channels 加载，后端返回的是扁平 Channel[]） */}
            {channels && channels.length > 0 && (
              <div className="mt-2 space-y-0.5 px-2">
                {channels.map((ch) => {
                  const active = selectedChannel === ch.id;
                  return (
                    <button
                      key={ch.id}
                      onClick={() => setChannel(ch.id)}
                      className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
                        active
                          ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                          : 'border-transparent text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
                      }`}
                    >
                      <span className="truncate">{ch.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
 
         </>
       )}
 
       {/* 导航入口已合并到下方的快捷操作中 */}
 
       {/* 频道区域与快捷操作之间的短分隔线 */}
       <div className="mt-3 mb-2 px-2">
         <div className="h-px w-10 rounded-full bg-[var(--od-border-strong)]" />
       </div>
 
       {/* 快捷操作 */}
       <div className="flex-1">
         <div className="mb-2 flex items-center justify-between px-2">
           <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
             快捷操作
           </h2>
           {/* 经典白天/黑夜切换开关 */}
           <ThemeToggle />
         </div>
         <div className="space-y-0.5">
          {/* 搜索页面和其他页面保持同一级入口 */}
          <Link
            to="/"
            className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
              isActive('/')
                ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            <SearchIcon className={`h-4 w-4 flex-shrink-0 ${isActive('/') ? 'text-[var(--od-accent)]' : ''}`} />
            <span className="truncate">搜索页面</span>
          </Link>

          {/* 通知中心入口：打开侧边通知面板 */}
          <button
            type="button"
            onClick={() => setNotificationOpen((prev) => !prev)}
            className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
              notificationOpen
                ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
            aria-label="打开通知中心"
          >
            <span className="relative inline-flex">
              <Bell
                className={`h-4 w-4 flex-shrink-0 ${
                  notificationOpen ? 'text-[var(--od-accent)]' : ''
                } ${hasUnreadNotifications ? 'notification-bell-wiggle' : ''}`}
              />
              {hasUnreadNotifications && (
                <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-[var(--od-error)] shadow-[0_0_0_2px_var(--od-bg)]" />
              )}
            </span>
            <span className="truncate">通知中心</span>
          </button>

          <Link
            to="/follows"
            className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
              isActive('/follows')
                ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            <Bookmark
              className={`h-4 w-4 flex-shrink-0 ${isActive('/follows') ? 'text-[var(--od-accent)]' : ''}`}
            />
            <span className="truncate">我的关注</span>
          </Link>
          <Link
            to="/settings"
            className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
              isActive('/settings')
                ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            <Settings className={`h-4 w-4 flex-shrink-0 ${isActive('/settings') ? 'text-[var(--od-accent)]' : ''}`} />
            <span className="truncate">设置</span>
          </Link>
          <Link
            to="/about"
            className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
              isActive('/about')
                ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            <Info className={`h-4 w-4 flex-shrink-0 ${isActive('/about') ? 'text-[var(--od-accent)]' : ''}`} />
            <span className="truncate">关于我们</span>
          </Link>
        </div>
      </div>

      {/* 底部登出按钮 */}
      <div className="mt-auto pt-2 border-t border-[var(--od-border-strong)]">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-[var(--od-error)] transition-all duration-200 hover:bg-[color-mix(in_oklab,var(--od-error)_10%,transparent)]"
        >
          <LogOut className="h-4 w-4 flex-shrink-0" />
          <span className="truncate font-medium">登出</span>
        </button>
      </div>

      {/* 通知中心面板：相对于侧边栏容器定位 */}
      <NotificationCenter
        open={notificationOpen}
        onClose={() => setNotificationOpen(false)}
        onUnreadChange={handleNotificationUnreadChange}
      />
    </div>
  );
}
