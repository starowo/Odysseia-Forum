import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  SlidersHorizontal,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { ScrollToTop } from '@/components/common/ScrollToTop';
import { ResizableSidebar } from '@/components/ResizableSidebar';
import { TopBar } from '@/components/layout/TopBar';
import { BannerCarousel } from '@/components/layout/BannerCarousel';
import { FilterBar } from '@/components/layout/FilterBar';
import { StatsBar } from '@/components/layout/StatsBar';
import { useSearchStore } from '@/features/search/store/searchStore';
import { ThreadCard } from '@/features/threads/components/ThreadCard';
import { ThreadListItem } from '@/features/threads/components/ThreadListItem';
import { ThreadCardSkeleton } from '@/features/threads/components/ThreadCardSkeleton';
import { searchApi } from '@/features/search/api/searchApi';
import { useSettings } from '@/hooks/useSettings';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { addSearchHistory } from '@/lib/searchHistory';
import bannerImage from '@/assets/images/banners/adfd891a-f9f7-4f9d-8d7c-975fb32a7f0d.png';

export function SearchPage() {
  const {
    query,
    selectedChannel,
    sortMethod,
    tagLogic,
    tagMode,
    tagStates,
    page,
    perPage,
    setQuery,
    setChannel,
    setSortMethod,
    setTagLogic,
    setTagMode,
    toggleTag,
    clearAllTags,
    setPage,
    setPerPage,
    clearFilters,
  } = useSearchStore();

  const [searchInput, setSearchInput] = useState(query);

  useEffect(() => {
    setSearchInput(query);
  }, [query]);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [timeFrom, setTimeFrom] = useState('');
  const [timeTo, setTimeTo] = useState('');
  const [openMode, setOpenMode] = useState<'app' | 'web'>('app');
  const searchInputRef = useRef<HTMLInputElement>(null);
  const { settings, updateSettings } = useSettings();

  // 默认Banner
  const defaultBanners = [
    {
      id: 'default-1',
      image: bannerImage,
      title: '欢迎来到 Odysseia 类脑搜索引擎',
      description: '探索精彩内容，发现无限可能',
    },
  ];

  // 获取选中的标签
  const includedTags = useMemo(() => {
    const tags: string[] = [];
    tagStates.forEach((state, tag) => {
      if (state === 'included') tags.push(tag);
    });
    return tags;
  }, [tagStates]);

  const excludedTags = useMemo(() => {
    const tags: string[] = [];
    tagStates.forEach((state, tag) => {
      if (state === 'excluded') tags.push(tag);
    });
    return tags;
  }, [tagStates]);

  // 使用真实API获取搜索结果
  const { data: searchData, isLoading } = useQuery({
    queryKey: ['search', query, selectedChannel, includedTags, excludedTags, tagLogic, sortMethod, page, perPage, timeFrom, timeTo],
    queryFn: () => searchApi.search({
      query: query || undefined,
      channel_ids: selectedChannel ? [selectedChannel] : undefined,
      include_tags: includedTags,
      exclude_tags: excludedTags,
      tag_logic: tagLogic,
      // 与 SearchParams.sort_method 对齐：relevance / last_active_desc / created_desc / reply_desc / reaction_desc
      sort_method: sortMethod,
      limit: perPage,
      offset: (page - 1) * perPage,
      created_after: timeFrom || undefined,
      created_before: timeTo || undefined,
    }),
    enabled: true, // 确保即使 queryKey 中有 null/undefined 也执行查询
    staleTime: 30 * 1000, // 30秒
  });

  // 从API响应中提取数据（与后端 SearchResponse.results 对齐）
  const threads = searchData?.results || [];
  const totalResults = searchData?.total || 0;
  const availableTags = searchData?.available_tags || [];
  const totalPages = Math.ceil(totalResults / perPage);

  // 处理搜索
  const handleSearch = useCallback(() => {
    const trimmedQuery = searchInput.trim();
    setQuery(trimmedQuery);
    // 保存到搜索历史
    if (trimmedQuery) {
      addSearchHistory(trimmedQuery);
    }
  }, [searchInput, setQuery]);

  // 从历史记录选择搜索
  const handleSelectHistory = (historyQuery: string) => {
    setSearchInput(historyQuery);
    setQuery(historyQuery);
    searchInputRef.current?.focus();
  };

  // 处理快捷搜索
  const handleQuickSearch = (template: string) => {
    // 如果搜索框为空，直接填充模板
    if (!searchInput.trim()) {
      setSearchInput(template);
    } else {
      // 如果搜索框有内容，在末尾添加空格和模板
      setSearchInput(searchInput + ' ' + template);
    }
    // 聚焦搜索框
    searchInputRef.current?.focus();
    toast.success('已添加搜索模板', {
      duration: 2000,
    });
  };

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
          setQuery('');
          toast.success('已清空搜索');
        }
      },
      description: '清空搜索',
    },
    {
      key: '/',
      callback: () => {
        searchInputRef.current?.focus();
      },
      description: '快速搜索',
    },
  ]);

  // 处理标签点击
  const handleTagClick = (tag: string) => {
    toggleTag(tag);
  };

  // 频道名称（暂时简化）
  const currentChannelName = selectedChannel || '全频道搜索';

  // 是否有活动的筛选条件
  const hasActiveFilters = query || selectedChannel || tagStates.size > 0;

  return (
    <div className="flex min-h-screen bg-[var(--od-bg)]">
      {/* 回到顶部按钮 */}
      <ScrollToTop />
      {/* 可调整大小的侧边栏 */}
      <ResizableSidebar
        defaultWidth={240}
        minWidth={200}
        maxWidth={400}
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
      >
        <AppSidebar />
      </ResizableSidebar>

      {/* 主内容区 */}
      <main className="flex-1 bg-[var(--od-bg)] pb-20 lg:ml-[240px]">
        {/* 顶部搜索栏 */}
        <TopBar
          searchValue={searchInput}
          onSearchChange={setSearchInput}
          onSearch={handleSearch}
          onMenuClick={() => setIsMobileOpen(true)}
          onQuickSearch={handleQuickSearch}
          searchInputRef={searchInputRef}
          onSelectHistory={handleSelectHistory}
        />

        {/* 频道标题栏 */}
        <div className="border-b border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-4 py-3">
          <h1 className="text-lg font-semibold text-[var(--od-text-primary)] transition-all duration-300">
            # {currentChannelName}
          </h1>
        </div>

        {/* Banner 轮播 - 只在主页显示（无搜索时） */}
        {!query && (
          <div className="p-4 animate-in fade-in slide-in-from-top-4 duration-500">
            <BannerCarousel banners={defaultBanners} />
          </div>
        )}

        {/* 筛选器 */}
        <div className="px-4 animate-in fade-in slide-in-from-top-4 duration-500" style={{ animationDelay: '100ms' }}>
          <FilterBar
            timeFrom={timeFrom}
            timeTo={timeTo}
            sortMethod={sortMethod}
            tagLogic={tagLogic}
            onTimeFromChange={setTimeFrom}
            onTimeToChange={setTimeTo}
            onSortMethodChange={(value) => setSortMethod(value as any)}
            onTagLogicChange={setTagLogic}
          />
        </div>

        {/* 标签筛选区 */}
        {availableTags.length > 0 && (
          <div className="border-b border-[var(--od-border)] bg-[var(--od-bg-secondary)] p-4 animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-[var(--od-text-secondary)]">标签筛选</span>
                {tagStates.size > 0 && (
                  <button
                    onClick={clearAllTags}
                    className="flex items-center gap-1 text-xs text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]"
                  >
                    <X className="h-3 w-3" />
                    清空
                  </button>
                )}
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-xs text-[var(--od-text-tertiary)]">
                  <input
                    type="checkbox"
                    checked={tagMode === 'excluded'}
                    onChange={(e) => setTagMode(e.target.checked ? 'excluded' : 'included')}
                    className="rounded"
                  />
                  排除模式
                </label>
                <button
                  onClick={() => setTagLogic(tagLogic === 'and' ? 'or' : 'and')}
                  className="flex items-center gap-2 text-xs text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]"
                >
                  <SlidersHorizontal className="h-4 w-4" />
                  {tagLogic === 'and' ? 'AND' : 'OR'}
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {availableTags.length > 0 ? (
                availableTags.map((tag) => {
                  const state = tagStates.get(tag);
                  return (
                    <button
                      key={tag}
                      onClick={() => handleTagClick(tag)}
                      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-all duration-200 hover:scale-105 ${
                        state === 'included'
                          ? 'bg-[#248046] text-white'
                          : state === 'excluded'
                            ? 'bg-[#da373c] text-white'
                            : 'bg-[#4e5058] text-[#dbdee1] hover:bg-[#6d6f78]'
                      }`}
                    >
                      {tag}
                    </button>
                  );
                })
              ) : (
                <p className="text-sm text-[var(--od-text-tertiary)]">暂无可用标签</p>
              )}
            </div>
          </div>
        )}

        {/* 搜索结果 */}
        <div className="p-4">
          {/* 统计信息栏 */}
          <div className="animate-in fade-in duration-300">
            <StatsBar
              totalCount={totalResults}
              perPage={perPage}
              openMode={openMode}
              layoutMode={settings.layoutMode}
              onPerPageChange={setPerPage}
              onOpenModeChange={setOpenMode}
              onLayoutModeChange={(mode) => updateSettings({ layoutMode: mode })}
            />
          </div>

          {/* 清空筛选按钮 */}
          {hasActiveFilters && (
            <div className="mb-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <button
                onClick={clearFilters}
                className="text-sm text-[#00a8fc] transition-all duration-200 hover:scale-105 hover:text-[#00c7fc] hover:underline"
              >
                清空所有筛选条件
              </button>
            </div>
          )}

          {/* 帖子网格/列表 - 添加淡入动画 */}
          {isLoading ? (
            <div className={settings.layoutMode === 'list' ? 'space-y-4 animate-in fade-in duration-300' : 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-in fade-in duration-300'}>
              {Array.from({ length: perPage }).map((_, i) => (
                <ThreadCardSkeleton key={i} />
              ))}
            </div>
          ) : threads.length > 0 ? (
            <div className={`animate-in fade-in duration-500 ${
              settings.layoutMode === 'list' 
                ? 'space-y-4' 
                : 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3'
            }`}>
              {threads.map((thread, index) => (
                <div
                  key={thread.thread_id}
                  className="animate-in fade-in slide-in-from-bottom-4"
                  style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'backwards' }}
                >
                  {settings.layoutMode === 'list' ? (
                    <ThreadListItem 
                      thread={thread} 
                      onTagClick={handleTagClick}
                      searchQuery={query}
                    />
                  ) : (
                    <ThreadCard 
                      thread={thread} 
                      onTagClick={handleTagClick}
                      searchQuery={query}
                    />
                  )}
                </div>
              ))}
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

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2 animate-in fade-in duration-300">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="rounded bg-[var(--od-border-strong)] p-2 text-[var(--od-text-primary)] transition-all duration-200 hover:scale-110 disabled:opacity-50 hover:bg-[var(--od-accent)]"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <span className="text-sm text-[var(--od-text-secondary)] transition-all duration-200">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="rounded bg-[var(--od-border-strong)] p-2 text-[var(--od-text-primary)] transition-all duration-200 hover:scale-110 disabled:opacity-50 hover:bg-[var(--od-accent)]"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
