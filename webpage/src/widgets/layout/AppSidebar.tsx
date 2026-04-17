import ServerIcon from '@/assets/images/icon/A90C044F8DDF1959B2E9078CB629C239.png';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { clearStoredAuthToken } from '@/shared/lib/authSession';
import { useChannels } from '@/shared/hooks/useChannels';
import { ThemeToggle } from '@/shared/ui/ThemeToggle';
import { AnimatedIcon } from '@/shared/ui/animation/AnimatedIcon';
import { WordLogoStatic } from '@/shared/ui/loaders/WordLogoStatic';
import {
  BookOpen,
  Compass,
  Dices,
  Info,
  LogOut,
  Search as SearchIcon,
  Settings,
  Tag as TagIcon,
  TestTube,
} from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useMemo } from 'react';

export function AppSidebar() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { params, setParams } = useSearchURLParams();
  const { data: channelsData } = useChannels();

  const groupedChannels = useMemo(() => {
    if (!channelsData?.channels) return [];
    interface Group {
      groupName: string;
      channels: typeof channelsData.channels;
    }
    const map = new Map<string, Group>();
    for (const c of channelsData.channels) {
      const gid = c.groupId || 'other';
      if (!map.has(gid)) {
        map.set(gid, { groupName: c.groupName || '其他区', channels: [] });
      }
      map.get(gid)!.channels.push(c);
    }
    return Array.from(map.values());
  }, [channelsData?.channels]);

  const currentURLParams = new URLSearchParams(location.search);
  const isFollowsPage = location.pathname === '/me' && currentURLParams.get('tab') === 'follows';
  const activeChannelId = params.channel;

  const handleLogout = async () => {
    try {
      const { authApi } = await import('@/features/auth/api/authApi');
      await authApi.logout();
    } catch (error) {
      console.error('Backend logout failed:', error);
    }
    clearStoredAuthToken();
    window.location.href = '/login';
  };

  const isActive = (path: string) => location.pathname === path;



  const clearChannelSelection = () => {
    if (isFollowsPage) {
      const nextParams = new URLSearchParams(location.search);
      nextParams.delete('channel');
      navigate(`/me?${nextParams.toString()}`);
      return;
    }

    if (location.pathname !== '/search') {
      navigateToSearchWithParams({ channel: null });
      return;
    }

    setParams({ channel: null });
  };

  const navigateToSearchWithParams = (updates: { channel?: string | null; query?: string }) => {
    const nextParams = new URLSearchParams();
    const nextQuery = updates.query ?? params.query ?? '';
    const nextChannel = updates.channel === undefined ? params.channel : updates.channel;

    if (nextQuery.trim()) nextParams.set('q', nextQuery.trim());
    if (nextChannel) nextParams.set('channel', nextChannel);

    navigate(`/search${nextParams.toString() ? `?${nextParams.toString()}` : ''}`);
  };

  const navItemClass = (active: boolean) =>
    `group flex w-full items-center gap-2 px-2 py-1.5 text-sm transition-colors duration-200 ${
      active
        ? 'font-medium text-[var(--od-text-primary)]'
        : 'text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
    }`;

  const navIndicatorClass = (active: boolean) =>
    `h-1.5 w-1.5 rounded-full transition-colors duration-200 ${
      active ? 'bg-[var(--od-accent)]' : 'bg-[var(--od-text-tertiary)]/45 group-hover:bg-[var(--od-text-secondary)]'
    }`;

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
              className={navItemClass(isActive('/'))}
            >
              <span className={navIndicatorClass(isActive('/'))} />
              <AnimatedIcon
                icon={Compass}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/') ? 'text-[var(--od-accent)]' : ''}`}
                animation="scale"
                trigger="hover"
              />
              <span className="truncate">广场</span>
            </Link>

            <Link
              to="/search"
              className={navItemClass(isActive('/search'))}
            >
              <span className={navIndicatorClass(isActive('/search'))} />
              <AnimatedIcon
                icon={SearchIcon}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/search') ? 'text-[var(--od-accent)]' : ''}`}
                animation="scale"
                trigger="hover"
              />
              <span className="truncate">搜索</span>
            </Link>

            <Link
              to="/draw"
              className={navItemClass(isActive('/draw'))}
            >
              <span className={navIndicatorClass(isActive('/draw'))} />
              <AnimatedIcon
                icon={Dices}
                className={`h-4 w-4 flex-shrink-0 ${isActive('/draw') ? 'text-[var(--od-accent)]' : ''}`}
                animation="pulse"
                trigger="hover"
              />
              <span className="truncate">随机抽卡</span>
            </Link>

            <Link
              to="/booklists"
              className={navItemClass(isActive('/booklists') || location.pathname.startsWith('/booklists/'))}
            >
              <span className={navIndicatorClass(isActive('/booklists') || location.pathname.startsWith('/booklists/'))} />
              <AnimatedIcon
                icon={BookOpen}
                className={`h-4 w-4 flex-shrink-0 ${
                  isActive('/booklists') || location.pathname.startsWith('/booklists/')
                    ? 'text-[var(--od-accent)]'
                    : ''
                }`}
                animation="scale"
                trigger="hover"
              />
              <span className="truncate">书单</span>
            </Link>

            <Link
              to="/tags"
              className={navItemClass(isActive('/tags'))}
            >
              <span className={navIndicatorClass(isActive('/tags'))} />
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
              className={navItemClass(isActive('/settings'))}
            >
              <span className={navIndicatorClass(isActive('/settings'))} />
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
              className={navItemClass(isActive('/about'))}
            >
              <span className={navIndicatorClass(isActive('/about'))} />
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
                className={navItemClass(isActive('/test'))}
              >
                <span className={navIndicatorClass(isActive('/test'))} />
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
          <div className="mb-2 flex items-center justify-between px-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
              频道
            </h2>
          </div>

          <div className="space-y-0.5">
            <button
              onClick={clearChannelSelection}
              className={navItemClass(!activeChannelId)}
            >
              <span className={navIndicatorClass(!activeChannelId)} />
              <span>全频道</span>
            </button>

            {groupedChannels.map((category) => (
              <div key={category.groupName} className="mt-4 first:mt-0">
                <div className="mb-1 px-2 text-[10px] font-bold uppercase tracking-widest text-[var(--od-text-tertiary)] opacity-60">
                  {category.groupName}
                </div>
                <div className="space-y-0.5">
                  {category.channels.map((channel) => {
                    const active = activeChannelId === channel.id;
                    return (
                      <button
                        key={channel.id}
                        onClick={() => {
                          const nextChannel = active ? null : channel.id;

                          if (isFollowsPage) {
                            const nextParams = new URLSearchParams(location.search);
                            if (nextChannel) {
                              nextParams.set('channel', nextChannel);
                            } else {
                              nextParams.delete('channel');
                            }
                            navigate(`/me?${nextParams.toString()}`);
                            return;
                          }

                          if (location.pathname !== '/search') {
                            navigateToSearchWithParams({ channel: nextChannel });
                            return;
                          }

                          setParams({ channel: nextChannel });
                        }}
                        className={navItemClass(active)}
                      >
                        <span className={navIndicatorClass(active)} />
                        <span className="truncate">{channel.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}

          </div>
        </div>


      </div>

      <div className="border-t border-[var(--od-border)] p-2">
        <div className="od-fluid-panel rounded-xl p-2 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center gap-1">
            <Link
              to="/me"
              className="group flex min-w-0 flex-1 items-center gap-2 overflow-hidden rounded-lg p-2 transition-colors hover:bg-[var(--od-bg-secondary)]"
            >
              <div className="relative h-8 w-8 flex-shrink-0">
                <img
                  src={
                    user?.avatar
                      ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
                      : 'https://cdn.discordapp.com/embed/avatars/0.png'
                  }
                  alt={user?.username}
                  className="h-full w-full rounded-full object-cover ring-2 ring-white/[0.08]"
                />
                <span className="absolute bottom-0 right-0 h-2 w-2 rounded-full border-2 border-white/[0.08] bg-green-500" />
              </div>
              <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
                <span className="truncate text-xs font-bold text-[var(--od-text-primary)]">
                  {user?.global_name || user?.username || 'Guest'}
                </span>
                <span className="truncate text-[10px] text-[var(--od-text-tertiary)]">@{user?.username}</span>
              </div>
            </Link>

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
    </div>
  );
}
