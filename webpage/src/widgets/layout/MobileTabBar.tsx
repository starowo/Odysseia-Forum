import { Dices, Home, Search, User } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

interface TabItem {
  id: string;
  path: string;
  icon: typeof Home;
  label: string;
}

const TABS: TabItem[] = [
  { id: 'home', path: '/', icon: Home, label: '广场' },
  { id: 'search', path: '/search', icon: Search, label: '搜索' },
  { id: 'draw', path: '/draw', icon: Dices, label: '抽卡' },
  { id: 'profile', path: '/me', icon: User, label: '我的' },
];

/**
 * 移动端底部 Tab 导航栏
 *
 * - 仅在 md 以下显示
 * - 支持 safe-area-inset-bottom（适配 iPhone 底部横条）
 * - 使用 react-router Link 进行页面导航
 */
export function MobileTabBar() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    if (path === '/search') return location.pathname === '/search';
    if (path === '/draw') return location.pathname === '/draw';
    return location.pathname === path;
  };

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-white/[0.06] backdrop-blur-xl md:hidden"
      style={{
        backgroundColor: 'color-mix(in srgb, var(--od-bg-secondary) 90%, transparent)',
        height: 'calc(4rem + env(safe-area-inset-bottom, 0px))',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      {TABS.map((tab) => {
        const active = isActive(tab.path);
        const Icon = tab.icon;
        return (
          <Link
            key={tab.id}
            to={tab.path}
            className={`flex w-full flex-col items-center justify-center space-y-1 transition-colors ${
              active
                ? 'text-[var(--od-accent)]'
                : 'text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            <Icon className={`h-5 w-5 ${active ? 'fill-[var(--od-accent)]/20' : ''}`} />
            <span className="text-[10px] font-medium">{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
