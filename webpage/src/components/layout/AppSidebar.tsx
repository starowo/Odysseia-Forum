import { Globe, Bookmark, Settings, Info, LogOut } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { UserCard } from '@/components/layout/UserCard';
import { useAuth } from '@/features/auth/hooks/useAuth';

export function AppSidebar() {
  const { user } = useAuth();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.clear();
    window.location.href = '/login';
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

      {/* 导航 */}
      <div className="mb-6">
        <h2 className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
          导航
        </h2>
        <div className="space-y-0.5">
          <Link
            to="/"
            className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
              isActive('/')
                ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            <Globe className={`h-4 w-4 flex-shrink-0 ${isActive('/') ? 'text-[var(--od-accent)]' : ''}`} />
            <span className="truncate">搜索页面</span>
          </Link>
        </div>
      </div>

      {/* 分隔线 */}
      <div className="my-2 h-px bg-[var(--od-border-strong)]" />

      {/* 快捷操作 */}
      <div className="flex-1">
        <h2 className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
          快捷操作
        </h2>
        <div className="space-y-0.5">
          <Link
            to="/follows"
            className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-sm transition-all duration-200 ${
              isActive('/follows')
                ? 'border-[var(--od-accent)] bg-[var(--od-card)] text-[var(--od-text-primary)]'
                : 'border-transparent text-[var(--od-text-tertiary)] hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            <Bookmark className={`h-4 w-4 flex-shrink-0 ${isActive('/follows') ? 'text-[var(--od-accent)]' : ''}`} />
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
    </div>
  );
}
