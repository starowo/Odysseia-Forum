import { ThreadCard } from '@/entities/thread/ThreadCard';
import { ThreadCardSkeleton } from '@/entities/thread/ThreadCardSkeleton';
import { ThreadListItem } from '@/entities/thread/ThreadListItem';
import { ThreadListItemSkeleton } from '@/entities/thread/ThreadListItemSkeleton';
import type { Thread } from '@/entities/thread/types';
import { MascotDialog } from '@/features/mascot/components/MascotDialog';
import { searchApi } from '@/features/search/api/searchApi';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { useSearchStore } from '@/features/search/store/searchStore';
import { useUserPreferences } from '@/features/preferences/hooks/useUserPreferences';
import {
  getDiscoveryPreferenceContext,
  resolveDiscoveryPreferencePatch,
} from '@/features/preferences/lib/discoveryPreferences';
import { GUILD_ID } from '@/shared/config/channelCategories.private';
import { useSettings } from '@/shared/hooks/useSettings';
import { addToken } from '@/shared/lib/searchTokenizer';
import { FluidDivider } from '@/shared/ui/FluidDivider';
import { ThreadPreviewOverlay } from '@/widgets/thread-preview/ThreadPreviewOverlay';
import { useInfiniteQuery } from '@tanstack/react-query';
import { Compass, Dices, Search, SlidersHorizontal } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

const defaultBanners = [
  {
    id: '1',
    image:
      'https://images.unsplash.com/photo-1614850523296-d8c1af93d400?auto=format&fit=crop&q=80&w=2070',
    title: '探索无限可能',
    description: '在 Odysseia 发现你感兴趣的内容',
  },
  {
    id: '2',
    image:
      'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?auto=format&fit=crop&q=80&w=2070',
    title: '类脑智能社区',
    description: '连接思想，共创未来',
  },
];

export function SearchPage() {
  const navigate = useNavigate();
  const { params, setParams } = useSearchURLParams();
  const {
    query,
    channel: selectedChannel,
    includeTags,
    excludeTags,
    includeAuthors,
    excludeAuthors,
    tagLogic,
    sortMethod,
    timeFrom,
    timeTo,
  } = params;

  const perPage = 24;
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const [showOnboarding, setShowOnboarding] = useState(() => {
    return !localStorage.getItem('od_onboarding_shown');
  });
  const [ignoreDiscoveryPreferences, setIgnoreDiscoveryPreferences] = useState(false);

  const { preferences } = useUserPreferences({ guildId: GUILD_ID });

  const hasExplicitFilters =
    includeTags.length > 0 ||
    excludeTags.length > 0 ||
    includeAuthors.length > 0 ||
    excludeAuthors.length > 0 ||
    !!timeFrom ||
    !!timeTo ||
    (sortMethod && sortMethod !== 'last_active_desc') ||
    (tagLogic && tagLogic !== 'and');

  const discoveryPreferenceContext = useMemo(
    () => getDiscoveryPreferenceContext(preferences),
    [preferences],
  );

  const discoveryPreferencePatch = useMemo(
    () => (ignoreDiscoveryPreferences
      ? null
      : resolveDiscoveryPreferencePatch({
        preferences,
        mode: 'browse-empty',
        query,
        selectedChannel,
        hasExplicitFilters,
      })),
    [preferences, query, selectedChannel, hasExplicitFilters, ignoreDiscoveryPreferences],
  );

  const effectiveSortMethod = discoveryPreferencePatch?.sort_method || sortMethod;
  const effectivePerPage = discoveryPreferencePatch?.limit || perPage;
  const effectiveChannelIds = selectedChannel
    ? [selectedChannel]
    : discoveryPreferencePatch?.channel_ids;
  const effectiveIncludeTags = includeTags.length > 0
    ? includeTags
    : (discoveryPreferencePatch?.include_tags || []);
  const effectiveExcludeTags = excludeTags.length > 0
    ? excludeTags
    : (discoveryPreferencePatch?.exclude_tags || []);

  const { setBannerList } = useSearchStore();
  const { settings } = useSettings();
  const [previewThread, setPreviewThread] = useState<Thread | null>(null);

  useEffect(() => {
    if (query.trim() || selectedChannel || hasExplicitFilters) {
      setIgnoreDiscoveryPreferences(false);
    }
  }, [query, selectedChannel, hasExplicitFilters]);

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

  const {
    data: searchData,
    isLoading,
    isError,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery<any, Error, any, any, number>({
    queryKey: [
      'search',
        query,
        selectedChannel,
        effectiveChannelIds?.join(',') || '',
        effectiveIncludeTags.join(','),
        effectiveExcludeTags.join(','),
        includeAuthors,
        excludeAuthors,
        tagLogic,
        effectiveSortMethod,
        effectivePerPage,
        timeFrom,
        timeTo,
        discoveryPreferenceContext?.signature || 'no-preferences',
      ],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      searchApi.search({
        query: query || undefined,
        channel_ids: effectiveChannelIds,
        include_tags: effectiveIncludeTags,
        exclude_tags: effectiveExcludeTags,
        tag_logic: tagLogic,
        sort_method: effectiveSortMethod,
        limit: effectivePerPage,
        offset: Number(pageParam) || 0,
        created_after: timeFrom || undefined,
        created_before: timeTo || undefined,
      }),
    getNextPageParam: (lastPage, allPages) => {
      const loadedCount = allPages.reduce(
        (sum: number, page: Awaited<ReturnType<typeof searchApi.search>>) => sum + (page.results?.length || 0),
        0,
      );
      return loadedCount < (lastPage.total || 0) ? loadedCount : undefined;
    },
    staleTime: 30 * 1000,
  });

  const results = useMemo<Thread[]>(() => {
    const mergedResults =
      (searchData?.pages.flatMap(
        (page: Awaited<ReturnType<typeof searchApi.search>>) => page.results || [],
      ) || []) as Thread[];

    const uniqueResults = new Map<string, Thread>();
    for (const thread of mergedResults) {
      if (!thread?.thread_id) continue;
      if (!uniqueResults.has(thread.thread_id)) {
        uniqueResults.set(thread.thread_id, thread);
      }
    }

    return Array.from(uniqueResults.values());
  }, [searchData]);
  const totalResults = Number(searchData?.pages?.[0]?.total || 0);

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || !hasNextPage) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { rootMargin: '300px 0px' },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage, results.length]);

  useEffect(() => {
    const bannerCarousel = searchData?.pages[0]?.banner_carousel;
    if (bannerCarousel && bannerCarousel.length > 0) {
      const apiBanners = bannerCarousel.map((banner: any) => ({
        id: banner.thread_id,
        image: banner.cover_image_url,
        title: banner.title,
        description: banner.description || '点击查看详情',
      }));
      setBannerList(apiBanners);
    } else if (defaultBanners.length > 0) {
      setBannerList(defaultBanners);
    }
  }, [searchData?.pages, setBannerList]);

  const handleTagClick = (tagName: string) => {
    const nextQuery = addToken(query || '', 'tag', tagName, 'include');
    setParams({ query: nextQuery });
  };

  const hasSearchFilters = !!query || hasExplicitFilters;

  const isPreferenceFilteredBrowse =
    !query.trim() &&
    !selectedChannel &&
    !hasExplicitFilters &&
    Boolean(discoveryPreferencePatch);

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
          <div className={settings.layoutMode === 'list' ? 'flex flex-col space-y-od-list-gap' : gridClass}>
            {Array.from({ length: 8 }).map((_, index) =>
              settings.layoutMode === 'list' ? (
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
            <div className={settings.layoutMode === 'list' ? 'flex flex-col space-y-od-list-gap pb-4' : gridClass}>
              {results.map((thread) =>
                settings.layoutMode === 'list' ? (
                  <ThreadListItem
                    key={thread.thread_id}
                    thread={thread}
                    onTagClick={handleTagClick}
                    searchQuery={query}
                    onAuthorClick={(author) => navigate(`/u/${author.id}`)}
                    onPreview={setPreviewThread}
                  />
                ) : (
                  <ThreadCard
                    key={thread.thread_id}
                    thread={thread}
                    onTagClick={handleTagClick}
                    searchQuery={query}
                    onAuthorClick={(author) => navigate(`/u/${author.id}`)}
                    onPreview={setPreviewThread}
                  />
                ),
              )}
            </div>

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

      {previewThread && (
        <ThreadPreviewOverlay thread={previewThread} onClose={() => setPreviewThread(null)} />
      )}
    </div>
  );
}
