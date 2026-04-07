import { ThreadCardSkeleton } from '@/entities/thread/ThreadCardSkeleton';
import { ThreadListItemSkeleton } from '@/entities/thread/ThreadListItemSkeleton';
import { ThreadResultsCollection } from '@/entities/thread/ThreadResultsCollection';
import { MascotDialog } from '@/features/mascot/components/MascotDialog';
import { usePreviewThread } from '@/features/search/hooks/usePreviewThread';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { useSearchResults } from '@/features/search/hooks/useSearchResults';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import { GUILD_ID } from '@/shared/config/channelCategories.private';
import { useLayoutMode } from '@/shared/hooks/useSettings';
import { addToken } from '@/shared/lib/searchTokenizer';
import { FluidDivider } from '@/shared/ui/FluidDivider';
import { Compass, Dices, Search, SlidersHorizontal } from 'lucide-react';
import { useState } from 'react';
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

  const layoutMode = useLayoutMode();

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

  const gridClass = 'grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

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
          <div className="mb-6 flex flex-col gap-3 rounded-[1.4rem] border border-[color-mix(in_srgb,var(--od-accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--od-accent)_7%,transparent)] px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--od-text-primary)]">当前探索结果已按你的发现偏好收束</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs leading-5 text-[var(--od-text-secondary)]">
                {discoveryPreferenceContext.preferredChannelIds.length > 0 && (
                  <span>频道 {discoveryPreferenceContext.preferredChannelIds.length} 个</span>
                )}
                {discoveryPreferenceContext.includeTags.length > 0 && (
                  <span>包含标签 {discoveryPreferenceContext.includeTags.length} 个</span>
                )}
                {discoveryPreferenceContext.excludeTags.length > 0 && (
                  <span>排除标签 {discoveryPreferenceContext.excludeTags.length} 个</span>
                )}
                {discoveryPreferenceContext.sortMethod && (
                  <span>默认排序已生效</span>
                )}
              </div>
            </div>

            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setIgnoreDiscoveryPreferences(true)}
                className="od-inline-action od-inline-action-ghost"
              >
                暂时忽略偏好
              </button>
              <button
                type="button"
                onClick={() => navigate('/me?tab=preferences')}
                className="od-inline-action od-inline-action-soft"
              >
                去调整偏好
              </button>
            </div>
          </div>
        )}

        {!hasSearchFilters && !isLoading && !isError && (
          <div className="mb-6 overflow-hidden rounded-[1.5rem] border border-[color-mix(in_srgb,var(--od-accent)_14%,transparent)] bg-[linear-gradient(145deg,color-mix(in_srgb,var(--od-accent)_8%,transparent),color-mix(in_srgb,var(--od-surface-raised)_92%,black_8%))] p-5 sm:p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-2xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-[color-mix(in_srgb,var(--od-accent)_18%,transparent)] bg-[color-mix(in_srgb,var(--od-accent)_10%,transparent)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--od-accent)]">
                  <Dices className="h-3.5 w-3.5" />
                  Surprise Discovery
                </div>
                <h2 className="mt-4 text-xl font-bold tracking-tight text-[var(--od-text-primary)]">想逛，但暂时没有明确关键词？</h2>
                <p className="mt-2 text-sm leading-6 text-[var(--od-text-secondary)]">
                  去随机抽卡页，把当前偏好当作安全池来抽一张或十连。它不会改写你的搜索框，只是给你一个更有趣的发现入口。
                </p>
              </div>

              <div className="flex shrink-0 flex-wrap items-center gap-2">
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
        )}

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
          <div className="flex min-h-[400px] flex-col items-center justify-center rounded-[1.5rem] bg-[var(--od-surface-input)] p-12 text-center">
            <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-red-500/10 text-red-500">
              <SlidersHorizontal className="h-10 w-10" />
            </div>
            <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">搜索出错了</h3>
            <p className="mb-6 text-[var(--od-text-secondary)]">暂时无法获取搜索结果，请稍后再试。</p>
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
          <div className="animate-in fade-in zoom-in-95 duration-500 flex min-h-[400px] flex-col items-center justify-center rounded-[1.5rem] bg-[var(--od-surface-input)] p-12 text-center">
            <div className="mb-4 text-[var(--od-text-tertiary)] opacity-20">
              <Search className="mx-auto h-24 w-24" />
            </div>
            <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">
              {hasSearchFilters ? '没有找到匹配的结果' : '开始你的探索之旅'}
            </h3>
            <p className="text-[var(--od-text-secondary)]">
              {hasSearchFilters ? '尝试调整搜索关键词或清空筛选条件' : '在上方搜索框输入内容，或从侧边栏选择频道'}
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
          我是这里的看板娘<b>类脑娘</b>！这里是全新的 Odysseia 论坛，拥有极强的搜索与筛选能力哦！
        </p>
        <ul className="list-disc space-y-1 pl-5 text-sm opacity-90">
          <li>
            试试顶部搜索框，支持{' '}
            <code className="rounded bg-[var(--od-bg-tertiary)] px-1 font-mono text-[0.9em]">$author:</code>、
            <code className="rounded bg-[var(--od-bg-tertiary)] px-1 font-mono text-[0.9em]">-$tag:</code> 等高级语法
          </li>
          <li>高级筛选已支持标签正反选、作者包含/排除、时间与排序组合</li>
          <li>点击卡片就能预览详情，不用跳页哦</li>
          {preferences && <li>你可以一键套用已保存的偏好频道和排序配置</li>}
        </ul>
      </MascotDialog>
    </div>
  );
}
