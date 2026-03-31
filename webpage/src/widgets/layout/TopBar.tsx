import { Menu, Search, SlidersHorizontal, Bell, Hash, Settings as SettingsIcon, Compass, Star } from 'lucide-react';
import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SearchSuggestions } from '@/features/search/components/SearchSuggestions';
import { NotificationCenter } from '@/features/notifications/components/NotificationCenter';
import { AnimatePresence } from 'framer-motion';
import { SearchTokenInput } from '@/shared/ui/SearchTokenInput';
import { AnimatedIcon } from '@/shared/ui/animation/AnimatedIcon';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type { Channel } from '@/entities/thread/types';

interface TopBarProps {
  onMenuClick: () => void;
}

/**
 * TopBar — 全局顶部搜索栏（V2）
 *
 * 布局对标草稿：
 *   header (h-20, justify-between)
 *     左侧: 移动端菜单 + 留空（将来放问候语 / 面包屑）
 *     右侧: 搜索框(默认 sm:w-80, 聚焦展开) + 通知铃铛
 *
 * 搜索框内右侧包含「漏斗」按钮。
 * 搜索建议 / 筛选面板均为 absolute 浮动下拉，互斥显示。
 */
export function TopBar({ onMenuClick }: TopBarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { params, setParams } = useSearchURLParams();

  const [searchInput, setSearchInput] = useState(params.query);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [hasUnreadNotifications, setHasUnreadNotifications] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Monitor notification count
  useEffect(() => {
    const handleNotificationCountMatch = (e: Event) => {
      const customEvent = e as CustomEvent;
      const count = customEvent.detail?.count || 0;
      setHasUnreadNotifications(count > 0);
    };

    window.addEventListener('odysseia:notification-count', handleNotificationCountMatch);
    return () => {
      window.removeEventListener('odysseia:notification-count', handleNotificationCountMatch);
    };
  }, []);

  // 同步 URL query → 本地输入
  useEffect(() => {
    setSearchInput(params.query);
  }, [params.query]);

  // 点击搜索容器外部时关闭所有浮窗
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
        setShowFilters(false);
        setIsFocused(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 频道列表
  const { data: channels } = useQuery({
    queryKey: ['meta', 'channels'],
    queryFn: async () => {
      const res = await apiClient.get<Channel[]>('/meta/channels');
      return res.data || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  // 执行搜索
  const handleSearch = useCallback(() => {
    const trimmed = searchInput.trim();
    if (location.pathname !== '/') {
      navigate(`/?q=${encodeURIComponent(trimmed)}`);
    } else {
      setParams({ query: trimmed });
    }
    setShowSuggestions(false);
  }, [searchInput, location.pathname, navigate, setParams]);

  // 漏斗按钮：互斥
  const toggleFilters = () => {
    setShowFilters((prev) => !prev);
    setShowSuggestions(false);
  };

  // 输入聚焦
  const handleInputFocus = () => {
    setIsFocused(true);
    setShowSuggestions(true);
    setShowFilters(false);
  };

  const needsFilter = location.pathname === '/' || location.pathname === '/follows';

  const hasActiveFilters =
    params.includeTags.length > 0 ||
    params.excludeTags.length > 0 ||
    params.timeFrom ||
    params.timeTo ||
    (params.sortMethod && params.sortMethod !== 'last_active_desc');

  // Breadcrumb logic
  const getBreadcrumb = () => {
    if (location.pathname === '/settings') {
      return { icon: SettingsIcon, label: '设置' };
    }
    if (location.pathname === '/follows') {
      return { icon: Star, label: '关注' };
    }
    if (location.pathname === '/') {
      if (params.channel && channels) {
         const channelInfo = channels.find(c => String(c.id) === String(params.channel));
         return { icon: Hash, label: channelInfo ? channelInfo.name : '全频道检索' };
      }
      return { icon: Compass, label: '探索' };
    }
    return null;
  };
  const breadcrumb = getBreadcrumb();

  return (
    <header className="flex h-[3.25rem] shrink-0 items-center justify-between px-3 sm:h-[4.25rem] sm:px-4">
      {/* ── 左侧：移动端菜单 + 面包屑 ── */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="rounded-lg p-2 text-[var(--od-text-secondary)] transition-all duration-200 hover:bg-white/[0.06] hover:text-[var(--od-text-primary)] lg:hidden"
          aria-label="打开菜单"
        >
          <AnimatedIcon icon={Menu} className="h-5 w-5" animation="rotate" trigger="click" />
        </button>
        
        {breadcrumb && (
          <div className="hidden sm:flex items-center gap-2 pl-2">
            <breadcrumb.icon className="h-4 w-4 text-[var(--od-text-tertiary)] hidden md:block" />
            <span className="text-sm font-semibold text-[var(--od-text-primary)] md:max-w-none max-w-[100px] truncate hidden md:block">
              {breadcrumb.label}
            </span>
          </div>
        )}
      </div>

      {/* ── 右侧：搜索框 + 通知 ── */}
      <div className="flex flex-1 justify-end items-center gap-2 md:gap-3" ref={searchContainerRef}>
        {/* 搜索框容器 — 弹性伸缩，常驻展示 */}
        <div className="relative flex-1 max-w-[480px]">
          <div
            className={`flex items-center overflow-hidden border w-full rounded-[100px] transition-all duration-300 ease-out ${
              isFocused
                ? 'border-[var(--od-accent)]/50 shadow-lg shadow-[var(--od-accent)]/10'
                : 'border-white/[0.06] hover:border-white/20'
            } bg-[var(--od-bg-tertiary)]`}
          >
            {/* 搜索图标 */}
            <div className={`shrink-0 p-2 transition-colors ${isFocused ? 'text-[var(--od-accent)]' : 'text-[var(--od-text-tertiary)]'}`}>
              <Search className="h-4 w-4" />
            </div>

            {/* 输入框（移动端也可见） */}
            <div className="min-w-0 flex-1">
              <SearchTokenInput
                value={searchInput}
                onChange={setSearchInput}
                onSearch={() => {
                  handleSearch();
                  setShowSuggestions(false);
                }}
                onFocus={handleInputFocus}
                placeholder="搜索标题、作者或内容..."
              />
            </div>

            {/* 漏斗按钮 */}
            {needsFilter && isFocused && (
              <button
                onClick={toggleFilters}
                className={`mr-2 shrink-0 rounded-md p-1.5 transition-all duration-200 ${
                  showFilters || hasActiveFilters
                    ? 'bg-[var(--od-accent)]/10 text-[var(--od-accent)]'
                    : 'text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
                aria-label="筛选"
                title="打开筛选面板"
              >
                <SlidersHorizontal className="h-4 w-4" />
                {hasActiveFilters && (
                  <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-[var(--od-accent)]" />
                )}
              </button>
            )}
          </div>

          {/* ── 搜索建议浮窗 ── */}
          <AnimatePresence>
            {showSuggestions && isFocused && (
              <SearchSuggestions
                currentQuery={searchInput}
                availableTags={[]}
                channels={channels || []}
                onSelect={(suggestion) => {
                  const newValue = searchInput + suggestion;
                  setSearchInput(newValue);
                  setShowSuggestions(false);
                }}
                onClose={() => setShowSuggestions(false)}
                inputRef={searchInputRef}
              />
            )}
          </AnimatePresence>

          {/* ── 筛选面板浮窗 ── */}
          {showFilters && (
            <div className="absolute right-0 top-full z-50 mt-2 w-[320px] rounded-2xl border border-white/[0.06] bg-[var(--od-bg-secondary)] p-4 shadow-2xl sm:w-[480px]">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[var(--od-text-primary)]">高级筛选</h3>
                {hasActiveFilters && (
                  <button
                    onClick={() => {
                      setParams({
                        sortMethod: 'last_active_desc',
                        timeFrom: '',
                        timeTo: '',
                        tagLogic: 'and',
                        includeTags: [],
                        excludeTags: [],
                      });
                    }}
                    className="text-xs text-[var(--od-accent)] hover:underline"
                  >
                    清空筛选
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* 排序方式 */}
                <div>
                  <label htmlFor="topbar-sort" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
                    排序方式
                  </label>
                  <select
                    id="topbar-sort"
                    value={params.sortMethod}
                    onChange={(e) => setParams({ sortMethod: e.target.value as any })}
                    className="w-full rounded-xl border border-white/[0.06] bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
                  >
                    <option value="last_active_desc">最近活跃</option>
                    <option value="created_desc">最新发布</option>
                    <option value="reply_desc">回复数</option>
                    <option value="reaction_desc">反应数</option>
                    <option value="relevance">相关度</option>
                  </select>
                </div>

                {/* 标签逻辑 */}
                <div>
                  <label htmlFor="topbar-tagLogic" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
                    标签逻辑
                  </label>
                  <select
                    id="topbar-tagLogic"
                    value={params.tagLogic}
                    onChange={(e) => setParams({ tagLogic: e.target.value as 'and' | 'or' })}
                    className="w-full rounded-xl border border-white/[0.06] bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
                  >
                    <option value="and">全部包含 (AND)</option>
                    <option value="or">任一即可 (OR)</option>
                  </select>
                </div>

                {/* 不早于 */}
                <div>
                  <label htmlFor="topbar-timeFrom" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
                    不早于
                  </label>
                  <input
                    id="topbar-timeFrom"
                    type="date"
                    value={params.timeFrom}
                    onChange={(e) => setParams({ timeFrom: e.target.value })}
                    className="w-full rounded-xl border border-white/[0.06] bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
                  />
                </div>

                {/* 不晚于 */}
                <div>
                  <label htmlFor="topbar-timeTo" className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-[var(--od-text-tertiary)]">
                    不晚于
                  </label>
                  <input
                    id="topbar-timeTo"
                    type="date"
                    value={params.timeTo}
                    onChange={(e) => setParams({ timeTo: e.target.value })}
                    className="w-full rounded-xl border border-white/[0.06] bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 通知铃铛 */}
        <div className="relative">
          <button
            onClick={() => setNotificationOpen((prev) => !prev)}
            className={`relative flex h-8 w-8 sm:h-[34px] sm:w-[34px] shrink-0 items-center justify-center rounded-full transition-colors border ${
              notificationOpen 
              ? 'border-[var(--od-accent)]/50 bg-[var(--od-accent)]/10 text-[var(--od-accent)]' 
              : 'border-white/[0.06] bg-[var(--od-bg-tertiary)] text-[var(--od-text-tertiary)] hover:border-white/20 hover:text-[var(--od-text-primary)]'
            }`}
          >
            <AnimatedIcon icon={Bell} className="h-4 w-4" animation="shake" trigger="hover" />
            {hasUnreadNotifications && (
              <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full border border-[var(--od-bg)] bg-red-500" />
            )}
          </button>
          <NotificationCenter
            open={notificationOpen}
            onClose={() => setNotificationOpen(false)}
          />
        </div>
      </div>
    </header>
  );
}
