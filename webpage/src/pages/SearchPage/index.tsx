import { ThreadCardSkeleton } from '@/entities/thread/ThreadCardSkeleton';
import { ThreadListItemSkeleton } from '@/entities/thread/ThreadListItemSkeleton';
import { ThreadResultsCollection } from '@/entities/thread/ThreadResultsCollection';
import { MascotDialog } from '@/features/mascot/components/MascotDialog';
import { usePreviewThread } from '@/features/search/hooks/usePreviewThread';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { useSearchResults } from '@/features/search/hooks/useSearchResults';
import { useCardGridClass, useSettings } from '@/shared/hooks/useSettings';
import { useMascotStore } from '@/features/mascot/store/mascotStore';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import { GUILD_ID } from '@/shared/config/channelCategories.private';
import { useLayoutMode } from '@/shared/hooks/useSettings';
import { addToken } from '@/shared/lib/searchTokenizer';
import { FluidDivider } from '@/shared/ui/FluidDivider';
import { Compass, Dices, LayoutGrid, Rows3, Search, SlidersHorizontal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

export function SearchPage() {
  const navigate = useNavigate();
  const { params, setParams } = useSearchURLParams();
  const {
    query,
    channel: selectedChannel,
  } = params;

  const [showOnboarding, setShowOnboarding] = useState(() => {
    return !localStorage.getItem('od_onboarding_shown');
  });

  const { preferences } = useUserPreferences({ guildId: GUILD_ID });
  const { openPreview } = usePreviewThread();
  const reactToSearch = useMascotStore((state) => state.reactToSearch);

  const layoutMode = useLayoutMode();
  const { updateSettings } = useSettings();
  const hasTriggeredSearchCueRef = useRef<string | null>(null);

  const {
    discoveryPreferenceContext,
    hasExplicitFilters,
    hasSearchFilters,
    ignoreDiscoveryPreferences,
    isPreferenceFilteredBrowse,
    loadMoreRef,
    queryState: {
      isLoading,
      isError,
      refetch,
      hasNextPage,
      isFetchingNextPage,
    },
    results,
    setIgnoreDiscoveryPreferences,
    totalResults,
  } = useSearchResults({ params, preferences });

  const handleCloseOnboarding = () => {
    setShowOnboarding(false);
    localStorage.setItem('od_onboarding_shown', 'true');
  };

  const handleApplyPreferences = () => {
    if (!preferences) {
      handleCloseOnboarding();
      return;
    }

    setIgnoreDiscoveryPreferences(false);
    setParams({
      query: '',
      channel: null,
      sortMethod: 'last_active_desc',
      timeFrom: '',
      timeTo: '',
      tagLogic: 'and',
    });

    toast.success('已切换到按偏好展示的探索模式');
    handleCloseOnboarding();
  };

  const handleTagClick = (tagName: string) => {
    const nextQuery = addToken(query || '', 'tag', tagName, 'include');
    setParams({ query: nextQuery });
  };

  const gridClass = useCardGridClass();

  useEffect(() => {
    if (isLoading) return;

    const normalizedQuery = query.trim();
    if (!normalizedQuery) {
      hasTriggeredSearchCueRef.current = null;
      return;
    }

    const cueKey = `${normalizedQuery}::${totalResults}::${isError ? 'error' : 'ok'}`;
    if (hasTriggeredSearchCueRef.current === cueKey) return;

    if (isError) {
      hasTriggeredSearchCueRef.current = cueKey;
      return;
    }

    reactToSearch(totalResults > 0 ? 'found' : 'empty', normalizedQuery);
    hasTriggeredSearchCueRef.current = cueKey;
  }, [isError, isLoading, query, reactToSearch, totalResults]);

  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden">
      <div className="animate-in fade-in duration-500 flex-1 p-4 sm:p-6 lg:p-8">
        <FluidDivider label="Search" tone="strong" className="mb-6" />
        <div className="mb-6 flex flex-col gap-4 pb-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
              <Compass className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">
                {query ? `搜索: ${query}` : '探索社区'}
              </h1>
              <div className="flex items-center gap-2 text-sm text-[var(--od-text-secondary)]">
                <span>找到 {totalResults} 条结果</span>
                {results.length > 0 && (
                  <>
                    <span className="opacity-30">•</span>
                    <span>已加载 {results.length} 条</span>
                  </>
                )}
                {isPreferenceFilteredBrowse && (
                  <>
                    <span className="opacity-30">•</span>
                    <span>已按偏好展示</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-1 rounded-full border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_76%,transparent)] p-1">
              <button
                type="button"
                onClick={() => updateSettings({ layoutMode: 'list' })}
                className={`inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  layoutMode === 'list'
                    ? 'bg-[var(--od-accent)] text-white'
                    : 'text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
                }`}
                aria-label="切换到列表展示"
                title="列表展示"
              >
                <Rows3 className="h-3.5 w-3.5" />
                列表
              </button>
              <button
                type="button"
                onClick={() => updateSettings({ layoutMode: 'grid' })}
                className={`inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  layoutMode === 'grid'
                    ? 'bg-[var(--od-accent)] text-white'
                    : 'text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
                }`}
                aria-label="切换到网格展示"
                title="网格展示"
              >
                <LayoutGrid className="h-3.5 w-3.5" />
                网格
              </button>
            </div>

            {ignoreDiscoveryPreferences && discoveryPreferenceContext && !query.trim() && !selectedChannel && !hasExplicitFilters && (
              <button
                type="button"
                onClick={() => setIgnoreDiscoveryPreferences(false)}
                className="od-inline-action od-inline-action-ghost"
              >
                恢复偏好展示
              </button>
            )}
            {hasSearchFilters && (
              <button
                onClick={() => {
                  setParams({
                    query: '',
                    sortMethod: 'last_active_desc',
                    timeFrom: '',
                    timeTo: '',
                    tagLogic: 'and',
                  });
                }}
                className="od-inline-action od-inline-action-soft"
              >
                清除所有筛选
              </button>
            )}
          </div>
        </div>

        {isPreferenceFilteredBrowse && discoveryPreferenceContext && (
          <section className="mb-7 px-1">
            <div className="od-inline-notice" data-tone="accent">
              <div className="od-inline-notice-head">
                <div className="min-w-0">
                  <div className="od-editorial-kicker">
                    <Compass className="h-3.5 w-3.5" />
                    Preference Filter Active
                  </div>
                  <p className="od-inline-notice-title mt-3">我先按你平时的口味帮你收了一下范围</p>
                  <p className="od-inline-notice-copy mt-2 max-w-3xl">
                    这样翻起来会省心一点点，不容易一上来就撞见你根本不想看的内容哦。
                  </p>
                </div>

                <div className="od-inline-notice-actions shrink-0 sm:justify-end">
                  <button
                    type="button"
                    onClick={() => setIgnoreDiscoveryPreferences(true)}
                    className="od-inline-action od-inline-action-soft"
                  >
                    暂时忽略偏好
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate('/me?tab=preferences')}
                    className="od-inline-action od-inline-action-ghost"
                  >
                    去调整偏好
                  </button>
                </div>
              </div>

              <div className="od-inline-notice-meta">
                {discoveryPreferenceContext.preferredChannelIds.length > 0 && (
                  <span className="od-pill-chip">频道 {discoveryPreferenceContext.preferredChannelIds.length} 个</span>
                )}
                {discoveryPreferenceContext.includeTags.length > 0 && (
                  <span className="od-pill-chip">包含标签 {discoveryPreferenceContext.includeTags.length} 个</span>
                )}
                {discoveryPreferenceContext.excludeTags.length > 0 && (
                  <span className="od-pill-chip">排除标签 {discoveryPreferenceContext.excludeTags.length} 个</span>
                )}
                {discoveryPreferenceContext.sortMethod && (
                  <span className="od-pill-chip">默认排序已生效</span>
                )}
              </div>
            </div>
          </section>
        )}

          <div className="mb-6 px-1">
            <div className="od-inline-notice" data-tone="accent">
              <div className="od-inline-notice-head">
                <div className="min-w-0">
                  <div className="od-editorial-kicker">
                    <Dices className="h-3.5 w-3.5" />
                    Surprise Discovery
                  </div>
                  <p className="od-inline-notice-title mt-3">一下子想不到搜什么吗？</p>
                  <p className="od-inline-notice-copy mt-2 max-w-3xl">
                    那就先去抽一抽呀。说不定运气好还能抽到个宝藏呢～
                  </p>
                </div>

                <div className="od-inline-notice-actions shrink-0 sm:justify-end">
                  <button
                    type="button"
                    onClick={() => navigate('/draw')}
                    className="od-inline-action od-inline-action-primary"
                  >
                    <Dices className="h-4 w-4" />
                    去抽卡
                  </button>
                </div>
              </div>
            </div>
          </div>

        {isLoading ? (
          <div className={layoutMode === 'list' ? 'flex flex-col space-y-od-list-gap' : gridClass}>
            {Array.from({ length: 8 }).map((_, index) =>
              layoutMode === 'list' ? (
                <ThreadListItemSkeleton key={index} />
              ) : (
                <ThreadCardSkeleton key={index} />
              ),
            )}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-red-500/10 text-red-500">
              <SlidersHorizontal className="h-10 w-10" />
            </div>
            <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">搜索出错了</h3>
            <p className="mb-6 text-[var(--od-text-secondary)]">暂时拉不到结果，稍后再试试吧。</p>
            <button
              onClick={() => refetch()}
              className="od-inline-action od-inline-action-primary px-6 py-3 text-sm"
            >
              重试搜索
            </button>
          </div>
        ) : results.length > 0 ? (
          <div className="flex flex-col gap-6">
            <ThreadResultsCollection
              threads={results}
              onTagClick={handleTagClick}
              searchQuery={query}
              onAuthorClick={(author) => navigate(`/u/${author.id}`)}
              onPreview={openPreview}
              gridClassName={gridClass}
              listClassName="flex flex-col space-y-od-list-gap pb-4"
            />

            <div ref={loadMoreRef} className="flex items-center justify-center py-8">
              {isFetchingNextPage ? (
                <span className="text-sm text-[var(--od-text-tertiary)]">正在加载更多结果…</span>
              ) : hasNextPage ? (
                <span className="text-sm text-[var(--od-text-tertiary)]">继续下滑以加载更多</span>
              ) : (
                <span className="text-sm text-[var(--od-text-tertiary)]">已经到底了</span>
              )}
            </div>
          </div>
        ) : (
          <div className="animate-in fade-in zoom-in-95 duration-500 flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 text-[var(--od-text-tertiary)] opacity-20">
              <Search className="mx-auto h-24 w-24" />
            </div>
            <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">
              {hasSearchFilters ? '没有找到匹配的结果' : '开始你的探索之旅吧～'}
            </h3>
            <p className="text-[var(--od-text-secondary)]">
              {hasSearchFilters ? '试试换个关键词，或者清掉筛选条件看看' : '在上面搜索框输入内容，或从侧边栏选个频道开始'}
            </p>
          </div>
        )}
      </div>

      <MascotDialog
        visible={showOnboarding}
        onClose={handleCloseOnboarding}
        emotion="hi"
        title="欢迎来到 Odysseia！"
        actionLabel={preferences ? '应用我的偏好' : '开始探索！'}
        onAction={preferences ? handleApplyPreferences : handleCloseOnboarding}
      >
        <p className="mb-3">
          我是这里的看板娘<b>类脑娘</b>！你要是想认真找东西，我最擅长陪你一起慢慢筛啦。
        </p>
        <ul className="list-disc space-y-1 pl-5 text-sm opacity-90">
          <li>
            顶上的搜索框很好用哦，像{' '}
            <code className="rounded bg-[var(--od-bg-tertiary)] px-1 font-mono text-[0.9em]">$author:</code>、
            <code className="rounded bg-[var(--od-bg-tertiary)] px-1 font-mono text-[0.9em]">-$tag:</code> 等高级语法
          </li>
          <li>筛选那边也能慢慢缩范围，标签、作者、时间和排序都可以一起配</li>
          <li>点卡片就能先偷看内容，不用来回跳页，轻松一点呀</li>
          {preferences && <li>如果你已经存过偏好，我也可以一键帮你套上</li>}
        </ul>
      </MascotDialog>
    </div>
  );
}
