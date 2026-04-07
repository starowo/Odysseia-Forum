import { NotificationCenter } from '@/features/notifications/components/NotificationCenter';
import {
  SearchSuggestions,
  type SearchSuggestionAction,
} from '@/features/search/components/SearchSuggestions';
import { SearchFilterPanel } from '@/features/search/components/SearchFilterPanel';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import type { SortMethod, TagLogic } from '@/features/search/hooks/useSearchParams';
import { useSearchAutocomplete } from '@/features/search/hooks/useSearchAutocomplete';
import { useTopBarFilterState } from '@/features/search/hooks/useTopBarFilterState';
import { useTopBarSearchController } from '@/features/search/hooks/useTopBarSearchController';
import { usePreviewStore } from '@/features/search/store/previewStore';
import { getPreferenceTagState } from '@/features/preferences/lib/discoveryPreferences';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import { GUILD_ID } from '@/shared/config/channelCategories.private';
import { SearchTokenInput } from '@/shared/ui/SearchTokenInput';
import { AnimatedIcon } from '@/shared/ui/animation/AnimatedIcon';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Bell,
  Compass,
  Hash,
  Menu,
  Search,
  Settings as SettingsIcon,
  SlidersHorizontal,
  User,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

interface TopBarProps {
  onMenuClick: () => void;
  sidebarCollapsed?: boolean;
}

export function TopBar({ onMenuClick, sidebarCollapsed = false }: TopBarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isSearchPage = location.pathname === '/search';
  const { params, setParams } = useSearchURLParams();
  const setPreviewThread = usePreviewStore((state) => state.setPreviewThread);
  const setPreviewThreadId = usePreviewStore((state) => state.setPreviewThreadId);
  const { preferences } = useUserPreferences({ guildId: GUILD_ID });

  const [notificationOpen, setNotificationOpen] = useState(false);
  const [hasUnreadNotifications, setHasUnreadNotifications] = useState(false);

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

  const needsFilter = isSearchPage;
  const preferenceTagState = useMemo(() => getPreferenceTagState(preferences), [preferences]);

  const {
    applyInputChange,
    clearFilters,
    clearHistory,
    closePanels,
    debouncedQuery,
    excludeAuthorDraft,
    excludeAuthorTokens,
    executeSearch,
    handleInputFocus,
    handleSearch,
    historyItems,
    includeAuthorDraft,
    includeAuthorTokens,
    isPanelOpen,
    removeAuthorToken,
    removeHistoryItem,
    searchContainerRef,
    searchInput,
    searchInputRef,
    setExcludeAuthorDraft,
    setIncludeAuthorDraft,
    setShowFilters,
    setShowSuggestions,
    showFilters,
    showSuggestions,
    submitAuthorDraft,
    toggleFilters,
    updateQuery,
    updateQueryFromTokenMutation,
  } = useTopBarSearchController({
    isSearchPage,
    navigate,
    params,
    setParams,
  });

  const {
    activeVirtualTag,
    availableTags,
    mergedTagState,
    preferenceSuggestedTags,
    suggestionAuthors,
    suggestionPreferencePatch,
    suggestionTags,
    suggestionThreads,
    virtualTagOriginChannelMap,
  } = useSearchAutocomplete({
    params,
    preferences,
    preferenceTagState,
    searchInput,
    debouncedQuery,
    showSuggestions,
  });

  const {
    handlePreferenceTagSyncToggle,
    syncPreferenceTags,
    toggleTagToken,
  } = useTopBarFilterState({
    params,
    preferenceExcludeTags: preferenceTagState.excludeTags,
    preferenceIncludeTags: preferenceTagState.includeTags,
    updateQuery,
    updateQueryFromTokenMutation,
    virtualTagOriginChannelMap,
  });

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

  const getBreadcrumb = () => {
    if (location.pathname === '/settings') {
      return { icon: SettingsIcon, label: '设置' };
    }
    if (location.pathname === '/me') {
      return { icon: User, label: '我的' };
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
    <header
      className={`fixed left-0 right-0 top-0 z-40 flex h-[3.25rem] shrink-0 items-center justify-between bg-transparent px-3 transition-[left] duration-300 sm:h-[4.25rem] sm:px-4 ${
        sidebarCollapsed ? 'lg:left-0' : 'lg:left-[170px]'
      }`}
    >
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
          <div className="od-chrome-surface flex min-h-[44px] items-center overflow-hidden rounded-[24px] border border-white/[0.06] transition-colors duration-200 hover:border-white/20">
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
                className="od-floating-glass absolute left-1/2 top-full z-50 mt-2 w-[calc(100vw-1.5rem)] max-w-[560px] -translate-x-1/2 overflow-hidden rounded-2xl border border-[var(--od-border-strong)] shadow-2xl sm:left-auto sm:right-0 sm:w-[560px] sm:max-w-none sm:translate-x-0"
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
                  <SearchFilterPanel
                    availableTags={availableTags}
                    excludeAuthorDraft={excludeAuthorDraft}
                    excludeAuthorTokens={excludeAuthorTokens}
                    hasPanelFilters={hasPanelFilters}
                    includeAuthorDraft={includeAuthorDraft}
                    includeAuthorTokens={includeAuthorTokens}
                    mergedExcludeTags={mergedTagState.excludeTags}
                    mergedIncludeTags={mergedTagState.includeTags}
                    onClearFilters={clearFilters}
                    onExcludeAuthorDraftChange={setExcludeAuthorDraft}
                    onIncludeAuthorDraftChange={setIncludeAuthorDraft}
                    onPreferenceTagSyncToggle={handlePreferenceTagSyncToggle}
                    onRemoveAuthorToken={removeAuthorToken}
                    onSortMethodChange={(value: SortMethod) => setParams({ sortMethod: value })}
                    onSubmitAuthorDraft={submitAuthorDraft}
                    onTagLogicChange={(value: TagLogic) => setParams({ tagLogic: value })}
                    onTimeFromChange={(value: string) => setParams({ timeFrom: value })}
                    onTimeToChange={(value: string) => setParams({ timeTo: value })}
                    onToggleTagToken={toggleTagToken}
                    preferenceExcludeTags={preferenceTagState.excludeTags}
                    preferenceIncludeTags={preferenceTagState.includeTags}
                    sortMethod={params.sortMethod}
                     syncPreferenceTags={syncPreferenceTags}
                    tagLogic={params.tagLogic}
                    timeFrom={params.timeFrom}
                    timeTo={params.timeTo}
                  />
                ) : (
                  <SearchSuggestions
                    currentQuery={searchInput}
                    availableTags={availableTags}
                    channels={[]}
                    authors={suggestionAuthors}
                    threads={suggestionThreads}
                      suggestedTags={searchInput.trim() ? suggestionTags : preferenceSuggestedTags}
                    history={historyItems}
                    onSelect={handleSuggestionSelect}
                    onRemoveHistory={(item) => {
                      removeHistoryItem(item.query);
                    }}
                    onClearHistory={() => {
                      clearHistory();
                    }}
                    onClose={closePanels}
                    inputRef={searchInputRef}
                    embedded
                    preferenceAware={Boolean(suggestionPreferencePatch)}
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
                : 'od-chrome-surface border-white/[0.06] text-[var(--od-text-tertiary)] hover:border-white/20 hover:text-[var(--od-text-primary)]'
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
