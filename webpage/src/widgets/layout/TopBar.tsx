import { NotificationCenter } from '@/features/notifications/components/NotificationCenter';
import { searchApi } from '@/features/search/api/searchApi';
import {
  SearchSuggestions,
  type SearchSuggestionAction,
} from '@/features/search/components/SearchSuggestions';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { usePreviewStore } from '@/features/search/store/previewStore';
import { ALL_VIRTUAL_TAGS } from '@/shared/config/navigation';
import {
  addSearchHistory,
  clearSearchHistory,
  getSearchHistory,
  removeSearchHistory,
} from '@/shared/lib/searchHistory';
import {
  addToken,
  parseSearchQuery,
  removeToken,
  type SearchToken,
} from '@/shared/lib/searchTokenizer';
import { SearchTokenInput } from '@/shared/ui/SearchTokenInput';
import { AnimatedIcon } from '@/shared/ui/animation/AnimatedIcon';
import { useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Bell,
  Compass,
  Hash,
  Menu,
  Search,
  Settings as SettingsIcon,
  SlidersHorizontal,
  Star,
  User,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

interface TopBarProps {
  onMenuClick: () => void;
}

function mergeUnique(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function tokenSignature(query: string) {
  return parseSearchQuery(query || '')
    .filter((token) => token.type !== 'text')
    .map((token) => `${token.mode || 'include'}:${token.type}:${token.value.trim()}`)
    .filter(Boolean)
    .sort()
    .join('|');
}

export function TopBar({ onMenuClick }: TopBarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isSearchPage = location.pathname === '/search';
  const { params, setParams } = useSearchURLParams();
  const { setPreviewThread, setPreviewThreadId } = usePreviewStore();

  const [searchInput, setSearchInput] = useState(params.query);
  const [debouncedQuery, setDebouncedQuery] = useState(params.query.trim());
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [hasUnreadNotifications, setHasUnreadNotifications] = useState(false);
  const [includeAuthorDraft, setIncludeAuthorDraft] = useState('');
  const [excludeAuthorDraft, setExcludeAuthorDraft] = useState('');
  const [historyItems, setHistoryItems] = useState(() => getSearchHistory());

  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const closePanels = useCallback(() => {
    setShowSuggestions(false);
    setShowFilters(false);
  }, []);

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

  useEffect(() => {
    setSearchInput(params.query);
  }, [params.query]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(searchInput.trim());
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (showSuggestions) {
      setHistoryItems(getSearchHistory());
    }
  }, [showSuggestions]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        closePanels();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [closePanels]);

  const activeVirtualTag = useMemo(() => {
    const tokens = parseSearchQuery(searchInput || '');
    const tagToken = tokens.find((token) => token.type === 'tag' && token.mode === 'include');
    if (!tagToken) return null;
    return ALL_VIRTUAL_TAGS.find((virtualTag) => virtualTag.name === tagToken.value);
  }, [searchInput]);

  const executeSearch = useCallback(
    (nextQuery: string) => {
      const trimmed = nextQuery.trim();
      setSearchInput(trimmed);

      if (!isSearchPage) {
        navigate(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : '/search');
      } else {
        setParams({ query: trimmed });
      }

      if (trimmed) {
        addSearchHistory(trimmed);
        setHistoryItems(getSearchHistory());
      }
      closePanels();
    },
    [closePanels, isSearchPage, navigate, setParams],
  );

  const applyInputChange = useCallback(
    (nextQuery: string) => {
      setSearchInput(nextQuery);

      const tokenChanged = tokenSignature(nextQuery) !== tokenSignature(params.query || '');
      if (!tokenChanged) return;

      const trimmed = nextQuery.trim();
      if (!isSearchPage) {
        navigate(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : '/search');
      } else {
        setParams({ query: trimmed });
      }
    },
    [isSearchPage, navigate, params.query, setParams],
  );

  const handleSearch = useCallback(() => {
    executeSearch(searchInput);
  }, [executeSearch, searchInput]);

  const handleSuggestionSelect = useCallback(
    (action: SearchSuggestionAction) => {
      if (action.type === 'open_thread') {
        if (action.thread) {
          setPreviewThread(action.thread);
        } else {
          setPreviewThreadId(action.threadId);
        }
        closePanels();
        return;
      }

      if (action.type === 'replace_query') {
        if (action.submit) {
          executeSearch(action.value);
        } else {
          applyInputChange(action.value);
          closePanels();
        }
        return;
      }

      const newValue = `${searchInput}${action.value}`.trim();
      applyInputChange(newValue);
      closePanels();
    },
    [applyInputChange, closePanels, executeSearch, searchInput, setPreviewThread, setPreviewThreadId],
  );

  const toggleFilters = () => {
    if (showFilters) {
      closePanels();
      return;
    }
    setShowSuggestions(false);
    setShowFilters(true);
  };

  const handleInputFocus = () => {
    setShowSuggestions(true);
    setShowFilters(false);
  };

  const needsFilter = isSearchPage || location.pathname === '/follows';

  const { data: filterMeta } = useQuery({
    queryKey: ['search-filter-meta', params.channel],
    queryFn: () =>
      searchApi.search({
        channel_ids: params.channel ? [params.channel] : undefined,
        limit: 1,
      }),
    staleTime: 5 * 60 * 1000,
  });

  const { data: channelTagCatalog = [] } = useQuery({
    queryKey: ['search-filter-meta', 'channel-tag-catalog'],
    queryFn: () => searchApi.getChannelTagCatalog(),
    enabled: !params.channel,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const globalAvailableTags = useMemo(() => {
    const tagSet = new Set<string>();
    for (const channel of channelTagCatalog) {
      for (const tag of channel.available_tags || []) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
      for (const tag of channel.virtual_tags || []) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
    }
    return Array.from(tagSet);
  }, [channelTagCatalog]);

  const virtualTagOriginChannelMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const channel of channelTagCatalog) {
      for (const tag of channel.virtual_tags || []) {
        if (tag?.trim() && !map.has(tag.trim())) {
          map.set(tag.trim(), channel.channel_id);
        }
      }
    }
    return map;
  }, [channelTagCatalog]);

  const availableTags = useMemo(() => {
    return mergeUnique([
      ...(filterMeta?.virtual_tags || []),
      ...(filterMeta?.available_tags || []),
      ...globalAvailableTags,
      ...params.includeTags,
      ...params.excludeTags,
    ]);
  }, [filterMeta?.available_tags, filterMeta?.virtual_tags, globalAvailableTags, params.includeTags, params.excludeTags]);

  const { data: suggestionSearchData } = useQuery({
    queryKey: ['search-suggestions', debouncedQuery, params.channel],
    queryFn: () =>
      searchApi.search({
        query: debouncedQuery,
        channel_ids: params.channel ? [params.channel] : undefined,
        limit: 5,
        sort_method: 'relevance',
      }),
    enabled: showSuggestions && debouncedQuery.length > 0,
    staleTime: 30 * 1000,
    retry: false,
  });

  const suggestionThreads = useMemo(() => {
    return (suggestionSearchData?.results || []).slice(0, 5).map((thread) => ({
      thread_id: thread.thread_id,
      title: thread.title,
      snippet: thread.first_message_excerpt || '',
      thumbnail_url: thread.thumbnail_urls?.[0] || null,
      author_name:
        thread.author?.display_name ||
        thread.author?.global_name ||
        thread.author?.name ||
        '未知用户',
      author_avatar_url: thread.author?.avatar_url || null,
      source_thread: thread,
    }));
  }, [suggestionSearchData?.results]);

  const suggestionAuthors = useMemo(() => {
    const unique = new Map<string, { id: string; name: string; avatar_url?: string | null }>();

    for (const thread of suggestionSearchData?.results || []) {
      if (!thread.author) continue;
      const authorId = String(thread.author.id);
      if (unique.has(authorId)) continue;

      unique.set(authorId, {
        id: authorId,
        name: thread.author.display_name || thread.author.global_name || thread.author.name,
        avatar_url: thread.author.avatar_url || null,
      });

      if (unique.size >= 5) break;
    }

    return Array.from(unique.values());
  }, [suggestionSearchData?.results]);

  const suggestionTags = useMemo(() => {
    return mergeUnique([
      ...(suggestionSearchData?.virtual_tags || []),
      ...(suggestionSearchData?.available_tags || []),
    ]).slice(0, 5);
  }, [suggestionSearchData?.available_tags, suggestionSearchData?.virtual_tags]);

  const allQueryTokens = useMemo(() => parseSearchQuery(searchInput), [searchInput]);
  const includeAuthorTokens = useMemo(
    () => allQueryTokens.filter((token) => token.type === 'author' && token.mode === 'include'),
    [allQueryTokens],
  );
  const excludeAuthorTokens = useMemo(
    () => allQueryTokens.filter((token) => token.type === 'author' && token.mode === 'exclude'),
    [allQueryTokens],
  );

  const hasActiveFilters =
    params.includeTags.length > 0 ||
    params.excludeTags.length > 0 ||
    params.includeAuthors.length > 0 ||
    params.excludeAuthors.length > 0 ||
    !!params.timeFrom ||
    !!params.timeTo ||
    (params.sortMethod && params.sortMethod !== 'last_active_desc') ||
    (params.tagLogic && params.tagLogic !== 'and');

  const hasPanelFilters = hasActiveFilters;
  const isPanelOpen = showSuggestions || showFilters;

  const updateQueryFromTokenMutation = useCallback(
    (mutator: (tokens: SearchToken[]) => string) => {
      const nextQuery = mutator(parseSearchQuery(params.query || ''));
      setSearchInput(nextQuery);
      setParams({ query: nextQuery });
    },
    [params.query, setParams],
  );

  const toggleTagToken = useCallback(
    (tagName: string, mode: 'include' | 'exclude') => {
      updateQueryFromTokenMutation((tokens) => {
        const existing = tokens.find(
          (token) => token.type === 'tag' && token.value === tagName && token.mode === mode,
        );
        const virtualOriginChannelId = !params.channel
          ? virtualTagOriginChannelMap.get(tagName) || null
          : null;

        let nextQuery = params.query || '';
        if (existing) {
          nextQuery = removeToken(nextQuery, existing);
          if (virtualOriginChannelId) {
            const nextTokens = parseSearchQuery(nextQuery);
            const hasOtherVirtualFromSameOrigin = nextTokens.some(
              (token) =>
                token.type === 'tag'
                && token.mode === 'include'
                && virtualTagOriginChannelMap.get(token.value) === virtualOriginChannelId,
            );
            if (!hasOtherVirtualFromSameOrigin) {
              const channelToken = nextTokens.find(
                (token) =>
                  token.type === 'channel'
                  && token.mode === 'include'
                  && token.value === virtualOriginChannelId,
              );
              if (channelToken) {
                nextQuery = removeToken(nextQuery, channelToken);
              }
            }
          }
        } else {
          const opposite = tokens.find(
            (token) => token.type === 'tag' && token.value === tagName && token.mode !== mode,
          );
          if (opposite) {
            nextQuery = removeToken(nextQuery, opposite);
          }
          nextQuery = addToken(nextQuery, 'tag', tagName, mode);
          if (virtualOriginChannelId) {
            nextQuery = addToken(nextQuery, 'channel', virtualOriginChannelId, 'include');
          }
        }
        return nextQuery.trim();
      });
    },
    [params.channel, params.query, updateQueryFromTokenMutation, virtualTagOriginChannelMap],
  );

  const removeAuthorToken = useCallback(
    (token: SearchToken) => {
      const nextQuery = removeToken(params.query || '', token).trim();
      setSearchInput(nextQuery);
      setParams({ query: nextQuery });
    },
    [params.query, setParams],
  );

  const submitAuthorDraft = useCallback(
    (mode: 'include' | 'exclude') => {
      const draft = (mode === 'include' ? includeAuthorDraft : excludeAuthorDraft).trim();
      if (!draft) return;

      const nextQuery = addToken(params.query || '', 'author', draft, mode).trim();
      setSearchInput(nextQuery);
      setParams({ query: nextQuery });

      if (mode === 'include') {
        setIncludeAuthorDraft('');
      } else {
        setExcludeAuthorDraft('');
      }
    },
    [excludeAuthorDraft, includeAuthorDraft, params.query, setParams],
  );

  const getBreadcrumb = () => {
    if (location.pathname === '/settings') {
      return { icon: SettingsIcon, label: '设置' };
    }
    if (location.pathname === '/follows') {
      return { icon: Star, label: '关注' };
    }
    if (location.pathname === '/search') {
      if (activeVirtualTag) {
        return { icon: Hash, label: activeVirtualTag.name };
      }
      return { icon: Compass, label: '探索' };
    }
    if (location.pathname === '/') {
      return { icon: Compass, label: '广场' };
    }
    return null;
  };

  const breadcrumb = getBreadcrumb();

  return (
    <header className="flex h-[3.25rem] shrink-0 items-center justify-between px-3 sm:h-[4.25rem] sm:px-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="rounded-lg p-2 text-[var(--od-text-secondary)] transition-all duration-200 hover:bg-white/[0.06] hover:text-[var(--od-text-primary)] lg:hidden"
          aria-label="打开菜单"
        >
          <AnimatedIcon icon={Menu} className="h-5 w-5" animation="rotate" trigger="click" />
        </button>

        {breadcrumb && (
          <div className="hidden items-center gap-2 pl-2 sm:flex">
            <breadcrumb.icon className="hidden h-4 w-4 text-[var(--od-text-tertiary)] md:block" />
            <span className="hidden max-w-[100px] truncate text-sm font-semibold text-[var(--od-text-primary)] md:block md:max-w-none">
              {breadcrumb.label}
            </span>
          </div>
        )}
      </div>

      <div className="flex flex-1 items-center justify-end gap-2 md:gap-3" ref={searchContainerRef}>
        <div className="relative min-w-0 flex-1 max-w-[560px]">
          <div className="flex min-h-[44px] items-center overflow-hidden rounded-[24px] border border-white/[0.06] bg-[var(--od-bg-tertiary)] transition-all duration-200 hover:border-white/20">
            <div className="shrink-0 p-2 text-[var(--od-text-tertiary)]">
              <Search className="h-4 w-4" />
            </div>

            <div className="min-w-0 flex-1 overflow-hidden">
              <SearchTokenInput
                value={searchInput}
                onChange={applyInputChange}
                onSearch={() => {
                  handleSearch();
                  closePanels();
                }}
                onFocus={handleInputFocus}
                externalInputRef={searchInputRef}
                placeholder="搜索标题、作者或内容..."
                className="min-h-[40px] rounded-[24px] bg-transparent"
              />
            </div>

            {needsFilter && (
              <button
                onClick={toggleFilters}
                className={`relative mr-2 shrink-0 rounded-md p-1.5 transition-all duration-200 ${
                  showFilters || hasPanelFilters
                    ? 'bg-[var(--od-accent)]/10 text-[var(--od-accent)]'
                    : 'text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]'
                }`}
                aria-label="筛选"
                title="打开筛选面板"
              >
                <SlidersHorizontal className="h-4 w-4" />
                {hasPanelFilters && (
                  <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-[var(--od-accent)]" />
                )}
              </button>
            )}
          </div>

          <AnimatePresence>
            {isPanelOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.98 }}
                transition={{ type: 'spring', stiffness: 320, damping: 26 }}
                className="absolute left-1/2 top-full z-50 mt-2 w-[calc(100vw-1.5rem)] max-w-[560px] -translate-x-1/2 overflow-hidden rounded-2xl border border-white/[0.06] bg-[var(--od-bg-secondary)] shadow-2xl sm:left-auto sm:right-0 sm:w-[560px] sm:max-w-none sm:translate-x-0"
              >
                {needsFilter && (
                  <div className="flex items-center gap-2 border-b border-white/[0.06] p-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowSuggestions(true);
                        setShowFilters(false);
                      }}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                        showSuggestions
                          ? 'bg-[var(--od-accent)]/20 text-[var(--od-accent)]'
                          : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)]'
                      }`}
                    >
                      搜索建议
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowFilters(true);
                        setShowSuggestions(false);
                      }}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                        showFilters
                          ? 'bg-[var(--od-accent)]/20 text-[var(--od-accent)]'
                          : 'text-[var(--od-text-secondary)] hover:bg-[var(--od-bg-tertiary)]'
                      }`}
                    >
                      高级筛选
                    </button>
                  </div>
                )}

                {showFilters ? (
                  <div className="p-4">
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-[var(--od-text-primary)]">高级筛选</h3>
                      {hasPanelFilters && (
                        <button
                          onClick={() => {
                            setSearchInput('');
                            setIncludeAuthorDraft('');
                            setExcludeAuthorDraft('');
                            setParams({
                              query: '',
                              sortMethod: 'last_active_desc',
                              timeFrom: '',
                              timeTo: '',
                              tagLogic: 'and',
                            });
                          }}
                          className="text-xs text-[var(--od-accent)] hover:underline"
                        >
                          清空筛选
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
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

                    <div className="mt-4 space-y-4">
                      <div>
                        <div className="mb-2 flex items-center justify-between">
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
                            标签筛选
                          </h4>
                          <span className="text-[11px] text-[var(--od-text-tertiary)]">
                            点击标签切换包含 / 排除 / 取消，不在这里显示删除按钮
                          </span>
                        </div>
                        <div className="flex max-h-[180px] flex-wrap gap-2 overflow-y-auto rounded-2xl bg-[var(--od-bg-tertiary)] p-3">
                          {availableTags.length > 0 ? (
                            availableTags.map((tag) => {
                              const isIncluded = params.includeTags.includes(tag);
                              const isExcluded = params.excludeTags.includes(tag);

                              return (
                                <div key={tag} className="flex items-center rounded-full bg-[var(--od-bg-secondary)] p-1">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      if (isIncluded) {
                                        toggleTagToken(tag, 'exclude');
                                        return;
                                      }
                                      if (isExcluded) {
                                        toggleTagToken(tag, 'exclude');
                                        return;
                                      }
                                      toggleTagToken(tag, 'include');
                                    }}
                                    className={`rounded-full px-3 py-1 text-xs transition-colors ${
                                      isIncluded
                                        ? 'bg-emerald-500/20 text-emerald-300'
                                        : isExcluded
                                          ? 'bg-rose-500/20 text-rose-300'
                                          : 'text-[var(--od-text-secondary)] hover:bg-emerald-500/10 hover:text-emerald-300'
                                    }`}
                                  >
                                    {isIncluded ? '✓ ' : isExcluded ? '✕ ' : ''}{tag}
                                  </button>
                                </div>
                              );
                            })
                          ) : (
                            <span className="text-sm text-[var(--od-text-tertiary)]">当前上下文暂时没有可用标签</span>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div>
                          <label className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
                            <User className="h-3.5 w-3.5" />
                            包含作者
                          </label>
                          <div className="flex gap-2">
                            <input
                              value={includeAuthorDraft}
                              onChange={(e) => setIncludeAuthorDraft(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  submitAuthorDraft('include');
                                }
                              }}
                              placeholder="输入昵称或用户名"
                              className="w-full rounded-xl border border-white/[0.06] bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
                            />
                            <button
                              type="button"
                              onClick={() => submitAuthorDraft('include')}
                              className="rounded-xl bg-emerald-500/20 px-3 text-sm text-emerald-300 transition-colors hover:bg-emerald-500/30"
                            >
                              添加
                            </button>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {includeAuthorTokens.map((token) => (
                              <button
                                key={`${token.mode}-${token.value}`}
                                type="button"
                                onClick={() => removeAuthorToken(token)}
                                className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300"
                              >
                                {token.value}
                                <X className="h-3 w-3" />
                              </button>
                            ))}
                          </div>
                        </div>

                        <div>
                          <label className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-[var(--od-text-tertiary)]">
                            <User className="h-3.5 w-3.5" />
                            排除作者
                          </label>
                          <div className="flex gap-2">
                            <input
                              value={excludeAuthorDraft}
                              onChange={(e) => setExcludeAuthorDraft(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  submitAuthorDraft('exclude');
                                }
                              }}
                              placeholder="输入昵称或用户名"
                              className="w-full rounded-xl border border-white/[0.06] bg-[var(--od-bg-tertiary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
                            />
                            <button
                              type="button"
                              onClick={() => submitAuthorDraft('exclude')}
                              className="rounded-xl bg-rose-500/20 px-3 text-sm text-rose-300 transition-colors hover:bg-rose-500/30"
                            >
                              添加
                            </button>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {excludeAuthorTokens.map((token) => (
                              <button
                                key={`${token.mode}-${token.value}`}
                                type="button"
                                onClick={() => removeAuthorToken(token)}
                                className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-3 py-1 text-xs text-rose-300"
                              >
                                {token.value}
                                <X className="h-3 w-3" />
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <SearchSuggestions
                    currentQuery={searchInput}
                    availableTags={availableTags}
                    channels={[]}
                    authors={suggestionAuthors}
                    threads={suggestionThreads}
                    suggestedTags={suggestionTags}
                    history={historyItems}
                    onSelect={handleSuggestionSelect}
                    onRemoveHistory={(item) => {
                      removeSearchHistory(item.query);
                      setHistoryItems(getSearchHistory());
                    }}
                    onClearHistory={() => {
                      clearSearchHistory();
                      setHistoryItems([]);
                    }}
                    onClose={closePanels}
                    inputRef={searchInputRef}
                    embedded
                  />
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="relative">
          <button
            onClick={() => setNotificationOpen((prev) => !prev)}
            className={`relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-colors sm:h-[34px] sm:w-[34px] ${
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
            onUnreadChange={(count) => {
              setHasUnreadNotifications(count > 0);
              window.dispatchEvent(
                new CustomEvent('odysseia:notification-count', {
                  detail: { count },
                }),
              );
            }}
          />
        </div>
      </div>
    </header>
  );
}
