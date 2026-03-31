import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Search } from 'lucide-react';
import { useKeyboardShortcuts } from '@/shared/hooks/useKeyboardShortcuts';
import { BannerCarousel } from '@/widgets/layout/BannerCarousel';
import { StatsBar } from '@/widgets/layout/StatsBar';
import { useSearchURLParams } from '@/features/search/hooks/useSearchParams';
import { usePreviewStore } from '@/features/search/store/previewStore';
import { useSearchStore } from '@/features/search/store/searchStore';
import { ThreadCard } from '@/entities/thread/ThreadCard';
import { ThreadListItem } from '@/entities/thread/ThreadListItem';
import { ThreadCardSkeleton } from '@/entities/thread/ThreadCardSkeleton';
import { searchApi } from '@/features/search/api/searchApi';
import { useSettings } from '@/shared/hooks/useSettings';
import { addToken, parseSearchQuery } from '@/shared/lib/searchTokenizer';
import type { Thread } from '@/entities/thread/types';
import bannerImage from '@/assets/images/banners/adfd891a-f9f7-4f9d-8d7c-975fb32a7f0d.png';

import { useMascotStore } from '@/features/mascot/store/mascotStore';
import { MascotDialog } from '@/features/mascot/components/MascotDialog';


// 默认Banner
const defaultBanners = [
  {
    id: 'default-1',
    image: bannerImage,
    title: '欢迎来到 Odysseia 类脑搜索引擎',
    description: '探索精彩内容，发现无限可能',
  },
];

/**
 * SearchPage — 搜索结果页
 *
 * V2 升级：
 *   - 不再自建布局（Sidebar / TopBar 由 AppShell 统一提供）
 *   - 只输出内容 sections：Banner → StatsBar → 列表
 *   - 所有搜索条件从 useSearchURLParams 读取
 */
export function SearchPage() {
  // ─── V2 数据源：URL 参数是搜索条件的单一来源 ───
  const { params, setParams, clearParams, hasActiveFilters } = useSearchURLParams();
  const { query, channel: selectedChannel, sortMethod, includeTags: urlIncludeTags, excludeTags: urlExcludeTags, tagLogic, timeFrom, timeTo } = params;

  // ─── 预览：独立 Store ───
  const { setPreviewThread } = usePreviewStore();

  // ─── Banner UI 状态：仍暂存在 searchStore（后续可继续精简） ───
  const { setMainBannerVisible, setActiveBanner, setBannerList } = useSearchStore();

  const reactToSearch = useMascotStore.getState().reactToSearch;

  // ─── 本地 UI 状态（不需要 URL 化） ───
  const [searchInput, setSearchInput] = useState(query);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [mergedThreads, setMergedThreads] = useState<Thread[]>([]);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(24);


  const searchInputRef = useRef<HTMLInputElement>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const { settings } = useSettings();

  // 当 URL 中的 query 变化时，同步到本地输入框
  useEffect(() => {
    if (query !== searchInput) {
      setSearchInput(query);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);



  // URL 搜索条件变化时，重置分页到第 1 页
  useEffect(() => {
    setPage(1);
    setMergedThreads([]);
  }, [query, selectedChannel, sortMethod, tagLogic, urlIncludeTags.join(','), urlExcludeTags.join(','), timeFrom, timeTo]);

  // 首次访问引导
  useEffect(() => {
    try {
      const seen = localStorage.getItem('od_onboarding_seen');
      if (!seen) setShowOnboarding(true);
    } catch (error) {
      console.error('Failed to read onboarding flag:', error);
    }
  }, []);

  // ─── token 解析（从搜索词中提取 $tag:xxx$ / $author:xxx$） ───
  const { keywordQuery, tokenIncludeTags, authorNameFromToken } = useMemo(() => {
    if (!query) {
      return {
        keywordQuery: '',
        tokenIncludeTags: [] as string[],
        authorNameFromToken: undefined as string | undefined,
      };
    }

    const tokens = parseSearchQuery(query);
    const textParts: string[] = [];
    const tagTokens: string[] = [];
    let authorToken: string | undefined;

    for (const token of tokens) {
      if (token.type === 'text') {
        textParts.push(token.value);
      } else if (token.type === 'tag') {
        tagTokens.push(token.value);
      } else if (token.type === 'author' && !authorToken) {
        authorToken = token.value;
      }
    }

    return {
      keywordQuery: textParts.join(' ').trim(),
      tokenIncludeTags: tagTokens,
      authorNameFromToken: authorToken,
    };
  }, [query]);

  // ─── 搜索请求：以 URL 参数为唯一 queryKey ───
  const { data: searchData, isLoading, isError, isFetching, refetch, isPlaceholderData } = useQuery({
    queryKey: ['search', query, selectedChannel, urlIncludeTags, urlExcludeTags, tagLogic, sortMethod, page, perPage, timeFrom, timeTo],
    queryFn: () =>
      searchApi.search({
        query: keywordQuery || undefined,
        channel_ids: selectedChannel ? [selectedChannel as any] : undefined,
        include_tags: Array.from(new Set([...urlIncludeTags, ...tokenIncludeTags])),
        exclude_tags: urlExcludeTags,
        tag_logic: tagLogic,
        sort_method: sortMethod,
        limit: perPage,
        offset: (page - 1) * perPage,
        created_after: timeFrom || undefined,
        created_before: timeTo || undefined,
        author_name: authorNameFromToken,
      }),
    enabled: true,
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });

  // 同步 Banner 数据到 Store，供 FloatingBanner 使用
  useEffect(() => {
    if (searchData?.banner_carousel && searchData.banner_carousel.length > 0) {
      const apiBanners = searchData.banner_carousel.map(b => ({
        id: b.thread_id,
        image: b.cover_image_url,
        title: b.title,
        description: (b as any).description || '点击查看详情',
      }));
      setActiveBanner(apiBanners[0]);
      setBannerList(apiBanners);
    } else if (defaultBanners.length > 0) {
      setActiveBanner(defaultBanners[0]);
      setBannerList(defaultBanners);
    }
  }, [searchData, setActiveBanner, setBannerList]);

  // Banner 轮播
  const displayBanners = useMemo(() => {
    const apiBanners = searchData?.banner_carousel?.map(b => ({
      id: b.thread_id,
      image: b.cover_image_url,
      title: b.title,
      description: (b as any).description || '点击查看详情',
    })) || [];
    return [...defaultBanners, ...apiBanners];
  }, [searchData]);

  // 看板娘反应
  useEffect(() => {
    if (!query) return;
    if (isLoading) {
      reactToSearch('start', query);
    } else if (searchData) {
      if (searchData.total > 0) {
        reactToSearch('found', query);
      } else {
        reactToSearch('empty', query);
      }
    }
  }, [searchData, isLoading, query, reactToSearch]);

  const totalResults = searchData?.total || 0;

  const totalPages = Math.ceil(totalResults / perPage);

  // 合并多页搜索结果
  useEffect(() => {
    if (!searchData || isPlaceholderData) {
      if (page === 1 && !isPlaceholderData) setMergedThreads([]);
      return;
    }
    const currentThreads = searchData.results || [];
    if (page === 1) {
      setMergedThreads(currentThreads);
      return;
    }
    setMergedThreads((prev) => {
      if (!prev || prev.length === 0) return currentThreads;
      const existingIds = new Set(prev.map((t) => t.thread_id));
      const newThreads = currentThreads.filter((t) => !existingIds.has(t.thread_id));
      return [...prev, ...newThreads];
    });
  }, [searchData, page]);

  // 无缝滚动加载
  useEffect(() => {
    const currentRef = loadMoreRef.current;
    if (!currentRef) return;
    if (isLoading || isError || isFetching) return;
    if (page >= totalPages) return;
    if (mergedThreads.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetching && page < totalPages) {
          setPage(page + 1);
        }
      },
      { threshold: 0.1, rootMargin: '200px' }
    );

    observer.observe(currentRef);
    return () => observer.disconnect();
  }, [isLoading, isError, isFetching, page, totalPages, mergedThreads.length]);

  // 键盘快捷键
  useKeyboardShortcuts([
    {
      key: 'k',
      ctrl: true,
      meta: true,
      callback: () => {
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      },
      description: '聚焦搜索框',
    },
    {
      key: 'Escape',
      callback: () => {
        if (searchInput || query) {
          setSearchInput('');
          clearParams();
          toast.success('已清空搜索');
        }
      },
      description: '清空搜索',
    },
  ]);

  // 标签点击 - 从卡片点击时添加到搜索框
  const handleTagClick = (tag: string) => {
    const newQuery = addToken(searchInput, 'tag', tag);
    setParams({ query: newQuery });
    toast.success(`已添加标签：${tag}`, { duration: 2000 });
  };

  const handleCloseOnboarding = () => {
    try {
      localStorage.setItem('od_onboarding_seen', '1');
    } catch (error) {
      console.error('Failed to save onboarding flag:', error);
    }
    setShowOnboarding(false);
  };

  const currentChannelName = selectedChannel || '全频道搜索';

  // 监听主 Banner 可见性
  const bannerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setMainBannerVisible(entry.isIntersecting);
      },
      { threshold: 0 }
    );
    if (bannerRef.current) observer.observe(bannerRef.current);
    return () => observer.disconnect();
  }, [setMainBannerVisible, query]);

  // 当有搜索词时，主 Banner 不渲染，强制设置 isMainBannerVisible 为 true
  useEffect(() => {
    if (query) setMainBannerVisible(true);
  }, [query, setMainBannerVisible]);

  // perPage 变化处理
  const handlePerPageChange = useCallback((newPerPage: number) => {
    const safePerPage = Math.min(100, Math.max(1, newPerPage || 1));
    setPerPage(safePerPage);
    setPage(1);
    setMergedThreads([]);
  }, []);

  // --- Virtualization State ---
  const [containerWidth, setContainerWidth] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      setContainerWidth(entries[0].contentRect.width);
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const cols = useMemo(() => {
    if (settings.layoutMode === 'list') return 1;
    if (containerWidth === 0) {
      if (typeof window === 'undefined') return 4;
      const w = window.innerWidth;
      if (w < 640) return 2;
      if (w < 1024) return 3;
      if (settings.sidebarCollapsed || w > 1280) return 5;
      return 4;
    }
    if (containerWidth < 640) return 2;
    if (containerWidth < 1024) return 3;
    if (settings.sidebarCollapsed || containerWidth > 1280) return 5;
    return 4;
  }, [containerWidth, settings.layoutMode, settings.sidebarCollapsed]);

  const rowCount = Math.ceil(mergedThreads.length / cols);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => document.getElementById('main-scroll-container') as HTMLElement,
    estimateSize: () => settings.layoutMode === 'list' ? 120 : 360,
    overscan: 3,
  });

  // ─── 渲染：不再包含 Sidebar / TopBar，直接输出内容 sections ───
  return (
    <div>
      {/* 频道标题栏 */}
      <div className="border-b border-white/[0.06] px-4 py-3 sm:px-8 sm:pt-6">
        <h1 className="text-lg font-semibold text-[var(--od-text-primary)] transition-all duration-300">
          # {currentChannelName}
        </h1>
      </div>

      {/* Banner 轮播 - 只在无搜索时显示 */}
      {!query && (
        <div ref={bannerRef} className="p-4 animate-in fade-in slide-in-from-top-4 duration-500">
          <BannerCarousel
            banners={displayBanners}
            onBannerClick={(banner) => {
              if (banner.id.startsWith('default-')) return;
              const thread = searchData?.results?.find(t => t.thread_id === banner.id);
              if (thread) {
                setPreviewThread(thread);
              } else {
                toast.error('无法预览该帖子');
              }
            }}
          />
        </div>
      )}

      {/* 搜索结果 */}
      <div className="p-4">
        <div className="animate-in fade-in duration-300">
          <StatsBar
            totalCount={totalResults}
            perPage={perPage}
            currentPage={page}
            totalPages={totalPages}
            onPerPageChange={handlePerPageChange}
          />
        </div>

        {/* 清空筛选按钮 */}
        {hasActiveFilters && (
          <div className="mb-4 animate-in fade-in slide-in-from-top-2 duration-300">
            <button
              onClick={() => {
                setSearchInput('');
                clearParams();
              }}
              className="text-sm text-[#00a8fc] transition-all duration-200 hover:scale-105 hover:text-[#00c7fc] hover:underline"
            >
              清空所有筛选条件
            </button>
          </div>
        )}

        {/* 搜索结果列表 */}
        {isLoading ? (
          <div
            className={
              settings.layoutMode === 'list'
                ? 'space-y-4 animate-in fade-in duration-300'
                : `grid grid-cols-2 gap-4 sm:grid-cols-3 ${settings.sidebarCollapsed ? 'lg:grid-cols-5' : 'lg:grid-cols-4'
                } animate-in fade-in duration-300`
            }
          >
            {Array.from({ length: perPage }).map((_, i) => (
              <ThreadCardSkeleton key={i} />
            ))}
          </div>
        ) : isError ? (
          <div className="flex min-h-[400px] items-center justify-center rounded-lg bg-[var(--od-card)] p-8 animate-in fade-in duration-300">
            <div className="text-center">
              <Search className="mx-auto mb-4 h-16 w-16 text-[var(--od-text-tertiary)]" />
              <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">
                搜索出错
              </h3>
              <p className="mb-4 text-[var(--od-text-secondary)]">
                搜索服务暂时不可用，请稍后重试。
              </p>
              <button
                type="button"
                onClick={() => refetch()}
                className="rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)]"
              >
                重试
              </button>
            </div>
          </div>
        ) : mergedThreads.length > 0 ? (
          <div ref={containerRef} className="animate-in fade-in duration-300">
            <div
              style={{
                height: `${virtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const startIndex = virtualRow.index * cols;
                const rowItems = mergedThreads.slice(startIndex, startIndex + cols);

                // 静态声明 grid 类名以确保 Tailwind 能正确扫描不被 Purge
                const gridClassMap: Record<number, string> = {
                  1: 'grid gap-od-card-gap pb-od-card-gap grid-cols-1',
                  2: 'grid gap-od-card-gap pb-od-card-gap grid-cols-2',
                  3: 'grid gap-od-card-gap pb-od-card-gap grid-cols-3',
                  4: 'grid gap-od-card-gap pb-od-card-gap grid-cols-4',
                  5: 'grid gap-od-card-gap pb-od-card-gap grid-cols-5',
                  6: 'grid gap-od-card-gap pb-od-card-gap grid-cols-6',
                };
                const gridClass = gridClassMap[cols] || gridClassMap[5];

                return (
                  <div
                    key={virtualRow.key}
                    data-index={virtualRow.index}
                    ref={virtualizer.measureElement}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className={
                      settings.layoutMode === 'list'
                        ? 'flex flex-col space-y-od-list-gap pb-4'
                        : gridClass
                    }
                  >
                    {rowItems.map((thread) =>
                      settings.layoutMode === 'list' ? (
                        <ThreadListItem
                          key={thread.thread_id}
                          thread={thread}
                          onTagClick={handleTagClick}
                          searchQuery={query}
                          onAuthorClick={(authorName) => {
                            const newQuery = addToken(searchInput, 'author', authorName);
                            setParams({ query: newQuery });
                            toast.success(`已添加作者：${authorName}`, { duration: 2000 });
                          }}
                          onPreview={setPreviewThread}
                        />
                      ) : (
                        <ThreadCard
                          key={thread.thread_id}
                          thread={thread}
                          onTagClick={handleTagClick}
                          searchQuery={query}
                          onAuthorClick={(authorName) => {
                            const newQuery = addToken(searchInput, 'author', authorName);
                            setParams({ query: newQuery });
                            toast.success(`已添加作者：${authorName}`, { duration: 2000 });
                          }}
                          onPreview={setPreviewThread}
                        />
                      )
                    )}
                  </div>
                );
              })}
            </div>

            {/* 无缝加载触发器 */}
            {page < totalPages && (
              <div
                ref={loadMoreRef}
                className="col-span-full flex items-center justify-center py-8"
              >
                {isFetching ? (
                  <div className="flex items-center gap-2 text-sm text-[var(--od-text-secondary)]">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--od-accent)] border-t-transparent" />
                    <span>加载中...</span>
                  </div>
                ) : (
                  <div className="h-1" />
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex min-h-[400px] items-center justify-center rounded-lg bg-[var(--od-card)] p-8 animate-in fade-in duration-300">
            <div className="text-center">
              <Search className="mx-auto mb-4 h-16 w-16 text-[var(--od-text-tertiary)]" />
              <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">
                {hasActiveFilters ? '没有找到匹配的结果' : '开始搜索'}
              </h3>
              <p className="text-[var(--od-text-secondary)]">
                {hasActiveFilters
                  ? '尝试调整搜索条件或清空筛选'
                  : '输入关键词或选择频道开始探索'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 首次访问引导浮层 */}
      <MascotDialog
        visible={showOnboarding}
        onClose={handleCloseOnboarding}
        emotion="hi"
        title="欢迎来到 Odysseia！"
        actionLabel="开始探索！"
        onAction={handleCloseOnboarding}
      >
        <p className="mb-3">
          我是这里的看板娘<b>类脑娘</b>！这里是全新的 Odysseia 论坛，你可以像在 Discord 一样探索帖子，但拥有更强的搜索与筛选能力哦！
        </p>
        <ul className="list-disc space-y-1 pl-5 text-sm opacity-90">
          <li>
            试试顶部搜索框，支持 <code className="rounded bg-[var(--od-bg-tertiary)] px-1 font-mono text-[0.9em]">$author:</code> 等高级语法
          </li>
          <li>左侧可以筛选频道和标签，组合条件超方便</li>
          <li>点击卡片就能预览详情，不用跳页哦</li>
        </ul>
      </MascotDialog>
    </div>
  );
}
// End of SearchPage component
