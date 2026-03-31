import ServerIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { CHANNEL_CATEGORIES, VIRTUAL_TAG_CATEGORIES } from '@/shared/config/navigation';
import { addToken, parseSearchQuery, removeToken } from '@/shared/lib/searchTokenizer';
import { ThemeToggle } from '@/shared/ui/ThemeToggle';
import { AnimatedIcon } from '@/shared/ui/animation/AnimatedIcon';
import { WordLogoStatic } from '@/shared/ui/loaders/WordLogoStatic';
import {
  Bookmark,
  Info,
  LogOut,
  Search as SearchIcon,
  Settings,
  Tag as TagIcon,
  TestTube,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export function AppSidebar() {
  const { user } = useAuth();
  const location = useLocation();
  const { params, setParams } = useSearchURLParams();
  const searchInput = params.query || '';

  const parsedTokens = parseSearchQuery(searchInput);
  const activeTags = parsedTokens
    .filter((token) => token.type === 'tag' && token.mode === 'include')
    .map((token) => token.value);
  const activeChannelId = params.channel;

  const handleLogout = async () => {
    try {
      const { authApi } = await import('@/features/auth/api/authApi');
      await authApi.logout();
    } catch (error) {
      console.error('Backend logout failed:', error);
    }
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
  };

  const isActive = (path: string) => location.pathname === path;

  const clearChannelAndVirtualTags = () => {
    const nextQuery = parseSearchQuery(searchInput)
      .filter(
        (token) => !(token.type === 'tag' && token.mode === 'include'),
      )
      .map((token) => token.raw)
      .join(' ')
      .trim();

    setParams({ query: nextQuery, channel: null });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 px-3 py-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center overflow-hidden rounded-full shadow-md">
          <img src={ServerIcon} alt="Server Icon" className="h-full w-full object-cover" />
        </div>
        <div className="flex min-w-0 flex-col justify-center gap-1">
          <span className="truncate text-[12px] font-bold leading-none tracking-widest text-[var(--od-text-primary)]">
            类脑
          </span>
          <WordLogoStatic className="h-[11px] flex-shrink-0 text-[var(--od-text-primary)]" />
        </div>
      </div>

      <div className="scrollbar-invisible flex-1 overflow-y-auto px-3 py-2">
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between px-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
              主导航
            </h2>
            <ThemeToggle />
          </div>
          <div className="space-y-0.5">
            <Link
              to="/"
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                isActive('/')
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

            <Link
              to="/follows"
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                isActive('/follows')
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
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                isActive('/tags')
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
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                isActive('/settings')
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
              className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                isActive('/about')
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

            {import.meta.env.VITE_API_MOCKING === 'true' && (
              <Link
                to="/test"
                className={`group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                  isActive('/test')
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

        <div className="mb-6">
          <div className="space-y-0.5">
            <button
              onClick={clearChannelAndVirtualTags}
              className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                activeTags.length === 0 && !activeChannelId
                  ? 'bg-[var(--od-bg-tertiary)] font-medium text-[var(--od-text-primary)]'
                  : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  activeTags.length === 0 && !activeChannelId
                    ? 'bg-[var(--od-accent)]'
                    : 'bg-[var(--od-text-tertiary)]'
                }`}
              />
              <span>全频道</span>
            </button>

            {CHANNEL_CATEGORIES.map((category) => (
              <div key={category.name} className="mt-4 first:mt-0">
                <div className="mb-1 px-2 text-[10px] font-bold uppercase tracking-widest text-[var(--od-text-tertiary)] opacity-60">
                  {category.name}
                </div>
                <div className="space-y-0.5">
                  {category.channels.map((channel) => {
                    const active = activeChannelId === channel.id;
                    return (
                      <button
                        key={channel.id}
                        onClick={() => {
                          setParams({ channel: active ? null : channel.id });
                        }}
                        className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                          active
                            ? 'bg-[var(--od-bg-tertiary)] font-medium text-[var(--od-text-primary)] shadow-sm'
                            : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            active
                              ? 'bg-[var(--od-accent)]'
                              : 'border border-[var(--od-text-tertiary)] opacity-30'
                          }`}
                        />
                        <span className="truncate">{channel.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}

            {VIRTUAL_TAG_CATEGORIES.map((category) => (
              <div key={category.name} className="mt-4 first:mt-0">
                <div className="mb-1 px-2 text-[10px] font-bold uppercase tracking-widest text-[var(--od-text-tertiary)] opacity-60">
                  {category.name}
                </div>
                <div className="space-y-0.5">
                  {category.tags.map((tag) => {
                    const active = activeTags.includes(tag.name);
                    return (
                      <button
                        key={tag.id}
                        onClick={() => {
                          const existing = parseSearchQuery(searchInput).find(
                            (token) => token.type === 'tag' && token.value === tag.name && token.mode === 'include',
                          );

                          const nextQuery = existing
                            ? removeToken(searchInput, existing)
                            : addToken(searchInput, 'tag', tag.name, 'include');

                          setParams({ query: nextQuery.trim() });
                        }}
                        className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-all duration-200 ${
                          active
                            ? 'bg-[var(--od-bg-tertiary)] font-medium text-[var(--od-text-primary)] shadow-sm'
                            : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]'
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            active
                              ? 'bg-[var(--od-accent)]'
                              : 'border border-[var(--od-text-tertiary)] opacity-30'
                          }`}
                        />
                        <span className="truncate">{tag.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-2">
        <div className="flex items-center justify-between rounded-xl bg-[var(--od-bg-tertiary)] p-2 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="relative h-8 w-8 flex-shrink-0">
              <img
                src={
                  user?.avatar
                    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
                    : 'https://cdn.discordapp.com/embed/avatars/0.png'
                }
                alt={user?.username}
                className="h-full w-full rounded-full object-cover ring-2 ring-[var(--od-bg-secondary)]"
              />
              <span className="absolute bottom-0 right-0 h-2 w-2 rounded-full border-2 border-[var(--od-bg-secondary)] bg-green-500" />
            </div>
            <div className="flex flex-col overflow-hidden">
              <span className="truncate text-xs font-bold text-[var(--od-text-primary)]">
                {user?.global_name || user?.username || 'Guest'}
              </span>
              <span className="truncate text-[10px] text-[var(--od-text-tertiary)]">@{user?.username}</span>
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
    </div>
  );
}
