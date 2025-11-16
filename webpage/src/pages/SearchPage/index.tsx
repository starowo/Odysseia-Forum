import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useQuery } from '@tanstack/react-query';
import { Search, SlidersHorizontal, X } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { ScrollToTop } from '@/components/common/ScrollToTop';
import { ResizableSidebar } from '@/components/ResizableSidebar';
import { TopBar } from '@/components/layout/TopBar';
import { BannerCarousel } from '@/components/layout/BannerCarousel';
import { FilterBar } from '@/components/layout/FilterBar';
import { StatsBar } from '@/components/layout/StatsBar';
import { useSearchStore, TagState } from '@/features/search/store/searchStore';
import { ThreadCard } from '@/features/threads/components/ThreadCard';
import { ThreadListItem } from '@/features/threads/components/ThreadListItem';
import { ThreadCardSkeleton } from '@/features/threads/components/ThreadCardSkeleton';
import { searchApi } from '@/features/search/api/searchApi';
import { useSettings } from '@/hooks/useSettings';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { addSearchHistory } from '@/lib/searchHistory';
import { addToken, parseSearchQuery } from '@/lib/searchTokenizer';
import { MarkdownText } from '@/components/common/MarkdownText';
import { LazyImage } from '@/components/common/LazyImage';
import type { Thread } from '@/types/thread.types';
import bannerImage from '@/assets/images/banners/adfd891a-f9f7-4f9d-8d7c-975fb32a7f0d.png';

interface ThreadPreviewOverlayProps {
  thread: Thread;
  onClose: () => void;
}

interface AdvancedSearchPanelProps {
  isOpen: boolean;
  timeFrom: string;
  timeTo: string;
  sortMethod: string;
  tagLogic: 'and' | 'or';
  tagMode: 'included' | 'excluded';
  availableTags: string[];
  tagStates: Map<string, TagState>;
  onTimeFromChange: (value: string) => void;
  onTimeToChange: (value: string) => void;
  onSortMethodChange: (value: string) => void;
  onTagLogicChange: (value: 'and' | 'or') => void;
  onTagModeChange: (value: 'included' | 'excluded') => void;
  onTagClick: (tag: string) => void;
  onClearAllTags: () => void;
  onQuickSearch?: (template: string) => void;
  enableQuickFill?: boolean;
}

// TopBar 下方的折叠面板 - 标签可点击填充到搜索框
function TopBarAdvancedPanel({
  isOpen,
  timeFrom,
  timeTo,
  sortMethod,
  tagLogic,
  tagMode,
  availableTags,
  tagStates,
  onTimeFromChange,
  onTimeToChange,
  onSortMethodChange,
  onTagLogicChange,
  onTagModeChange,
  onTagClick,
  onClearAllTags,
  onQuickSearch,
}: AdvancedSearchPanelProps) {
  const hasTags = availableTags.length > 0;

  return (
    <div
      className={`bg-[var(--od-bg-secondary)] transition-[max-height,opacity] duration-300 ${
        isOpen ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
      } overflow-hidden shadow-lg`}
    >
      <div className="px-4 pb-4 pt-2">
        <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)]/90 p-3 shadow-sm backdrop-blur-sm">
          <FilterBar
            timeFrom={timeFrom}
            timeTo={timeTo}
            sortMethod={sortMethod}
            tagLogic={tagLogic}
            onTimeFromChange={onTimeFromChange}
            onTimeToChange={onTimeToChange}
            onSortMethodChange={onSortMethodChange}
            onTagLogicChange={onTagLogicChange}
          />
          {hasTags && (
            <div className="mt-3 border-t border-[var(--od-border)] pt-3">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium text-[var(--od-text-secondary)]">
                    标签筛选
                  </span>
                  {tagStates.size > 0 && (
                    <button
                      type="button"
                      onClick={onClearAllTags}
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
                      onChange={(e) =>
                        onTagModeChange(e.target.checked ? 'excluded' : 'included')
                      }
                      className="rounded"
                    />
                    排除模式
                  </label>
                  <button
                    type="button"
                    onClick={() => onTagLogicChange(tagLogic === 'and' ? 'or' : 'and')}
                    className="flex items-center gap-2 text-xs text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]"
                  >
                    <SlidersHorizontal className="h-4 w-4" />
                    {tagLogic === 'and' ? 'AND' : 'OR'}
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableTags.map((tag) => {
                  const state = tagStates.get(tag);
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => onQuickSearch?.(tag)}
                      title="点击填充到搜索框"
                      className={`rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-200 hover:scale-105 ${
                        state === 'included'
                          ? 'bg-[var(--od-accent)] text-white'
                          : state === 'excluded'
                          ? 'bg-[var(--od-error)] text-white'
                          : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)] hover:bg-[var(--od-card-hover)]'
                      }`}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {!hasTags && (
            <p className="mt-3 text-xs text-[var(--od-text-tertiary)]">
              当前搜索结果暂时没有可用标签。
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// 主页面的固定面板 - Banner下方，标签用于筛选
function MainAdvancedPanel({
  timeFrom,
  timeTo,
  sortMethod,
  tagLogic,
  tagMode,
  availableTags,
  tagStates,
  onTimeFromChange,
  onTimeToChange,
  onSortMethodChange,
  onTagLogicChange,
  onTagModeChange,
  onTagClick,
  onClearAllTags,
}: Omit<AdvancedSearchPanelProps, 'isOpen' | 'onQuickSearch' | 'enableQuickFill'>) {
  const hasTags = availableTags.length > 0;

  return (
    <div className="px-4 animate-in fade-in slide-in-from-top-4 duration-500" style={{ animationDelay: '100ms' }}>
      <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-bg-secondary)]/90 p-3 shadow-sm backdrop-blur-sm">
        <FilterBar
          timeFrom={timeFrom}
          timeTo={timeTo}
          sortMethod={sortMethod}
          tagLogic={tagLogic}
          onTimeFromChange={onTimeFromChange}
          onTimeToChange={onTimeToChange}
          onSortMethodChange={onSortMethodChange}
          onTagLogicChange={onTagLogicChange}
        />
        {hasTags && (
          <div className="mt-3 border-t border-[var(--od-border)] pt-3">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-[var(--od-text-secondary)]">
                  标签筛选
                </span>
                {tagStates.size > 0 && (
                  <button
                    type="button"
                    onClick={onClearAllTags}
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
                    onChange={(e) =>
                      onTagModeChange(e.target.checked ? 'excluded' : 'included')
                    }
                    className="rounded"
                  />
                  排除模式
                </label>
                <button
                  type="button"
                  onClick={() => onTagLogicChange(tagLogic === 'and' ? 'or' : 'and')}
                  className="flex items-center gap-2 text-xs text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]"
                >
                  <SlidersHorizontal className="h-4 w-4" />
                  {tagLogic === 'and' ? 'AND' : 'OR'}
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {availableTags.map((tag) => {
                const state = tagStates.get(tag);
                return (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => onTagClick(tag)}
                    className={`rounded-full px-3 py-1.5 text-sm font-medium transition-all duration-200 hover:scale-105 ${
                      state === 'included'
                        ? 'bg-[var(--od-accent)] text-white'
                        : state === 'excluded'
                        ? 'bg-[var(--od-error)] text-white'
                        : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)] hover:bg-[var(--od-card-hover)]'
                    }`}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        {!hasTags && (
          <p className="mt-3 text-xs text-[var(--od-text-tertiary)]">
            当前搜索结果暂时没有可用标签。
          </p>
        )}
      </div>
    </div>
  );
}

// 预览浮层组件：负责上浮卡片的进出场动画 & 独立滚动
function ThreadPreviewOverlay({ thread, onClose }: ThreadPreviewOverlayProps) {
  // visible 用于控制「刚挂载时从 0 → 1」的入场动画
  const [visible, setVisible] = useState(false);
  const [closing, setClosing] = useState(false);

  // 挂载后下一帧再标记为可见，触发淡入+缩放动画
  useEffect(() => {
    const id = window.setTimeout(() => {
      setVisible(true);
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  const handleStartClose = () => {
    if (closing) return;
    setClosing(true);
    setVisible(false);
    // 等待动画结束再真正卸载
    window.setTimeout(() => {
      onClose();
    }, 220);
  };

  const authorName =
    thread.author?.display_name ??
    thread.author?.global_name ??
    thread.author?.name ??
    '未知用户';
  const guildId = thread.guild_id || import.meta.env.VITE_GUILD_ID || '@me';
  const discordUrl = `https://discord.com/channels/${guildId}/${thread.channel_id}/${thread.thread_id}`;

  return (
    <div
      className={`fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm px-3 sm:px-6 transition-opacity duration-250 ${
        closing || !visible ? 'opacity-0' : 'opacity-100'
      }`}
      onClick={handleStartClose}
    >
      <div
        className={`relative my-4 flex w-full max-w-4xl max-h-[90vh] flex-col overflow-hidden rounded-xl bg-[var(--od-card)] shadow-2xl sm:my-6 sm:rounded-2xl transform transition-all duration-250 ease-out ${
          closing || !visible
            ? 'scale-95 translate-y-4 opacity-0'
            : 'scale-100 translate-y-0 opacity-100'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          type="button"
          onClick={handleStartClose}
          className="absolute right-3 top-3 z-10 rounded-full bg-black/60 p-1.5 text-xs text-white shadow-md hover:bg-black/80"
          aria-label="关闭预览"
        >
          <X className="h-4 w-4" />
        </button>

        {/* 顶部大图 */}
        <div className="relative h-52 w-full overflow-hidden bg-[var(--od-bg-tertiary)] sm:h-64">
          {thread.thumbnail_url ? (
            <LazyImage
              src={thread.thumbnail_url}
              alt={thread.title}
              className="h-full w-full bg-black object-contain"
            />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-[#18191c] to-[#1e1f22]" />
          )}

          {thread.has_update && (
            <div className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-[#23a55a]/90 px-2.5 py-0.5 text-xs font-semibold text-white shadow-sm backdrop-blur-sm">
              <span className="inline-block h-2 w-2 rounded-full bg-white animate-[pulse_2.4s_ease-in-out_infinite]" />
              <span>有更新</span>
            </div>
          )}
        </div>

        {/* 正文区域 - 独立滚动 */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {/* 标题 */}
          <h2 className="mb-3 text-lg font-bold leading-snug text-[var(--od-text-primary)] sm:text-xl">
            {thread.is_following && (
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#f23f43]" />
            )}
            {thread.title}
          </h2>

          {/* 作者信息 */}
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-[var(--od-text-tertiary)] sm:text-sm">
            <span className="font-medium text-[var(--od-link)]">{authorName}</span>
            {thread.channel_id && (
              <>
                <span>·</span>
                <span>频道 {thread.channel_id}</span>
              </>
            )}
          </div>

          {/* 标签 */}
          {thread.tags && thread.tags.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
              {thread.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-md bg-[var(--od-bg-secondary)] px-2.5 py-1 text-xs font-medium text-[var(--od-text-secondary)]"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* 正文 Markdown */}
          {thread.first_message_excerpt && thread.first_message_excerpt.trim() !== '...' ? (
            <div className="od-md text-sm text-[var(--od-text-primary)]">
              <MarkdownText text={thread.first_message_excerpt} />
            </div>
          ) : (
            <p className="mt-2 text-sm text-[var(--od-text-tertiary)]">
              当前接口只返回首条消息的摘要，完整内容请在 Discord 中查看。
            </p>
          )}

          {/* 打开原帖按钮 */}
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={() => window.open(discordUrl, '_blank', 'noopener,noreferrer')}
              className="rounded-lg bg-[var(--od-accent)] px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)]"
            >
              在 Discord 中打开
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface SearchOnboardingOverlayProps {
  onClose: () => void;
}

function SearchOnboardingOverlay({ onClose }: SearchOnboardingOverlayProps) {
  return (
    <div
      className="fixed inset-0 z-[55] flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-[var(--od-border-strong)]/60 bg-[var(--od-card)] p-6 shadow-2xl animate-in fade-in zoom-in duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-3 text-xl font-bold text-[var(--od-text-primary)]">
          欢迎来到类脑搜索
        </h2>
        <p className="mb-4 text-sm text-[var(--od-text-secondary)]">
          这是 Odysseia 的新网页前端，你可以像在 Discord 一样探索帖子，但拥有更强的搜索与筛选能力。
        </p>
        <ul className="mb-5 list-disc space-y-2 pl-5 text-sm text-[var(--od-text-secondary)]">
          <li>
            使用顶部搜索框输入关键词，支持{' '}
            <code className="rounded bg-[var(--od-bg-tertiary)] px-1 text-[0.8em]">author:</code>{' '}
            等高级语法。
          </li>
          <li>左侧选择频道与标签，组合 AND / OR 条件精确筛选。</li>
          <li>点击任意卡片或列表项，可以打开预览浮层阅读完整内容。</li>
        </ul>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:scale-105 hover:bg-[var(--od-accent-hover)]"
          >
            知道了，开始探索
          </button>
          <p className="text-xs text-[var(--od-text-tertiary)]">
            此引导只会在本设备第一次访问时出现。
          </p>
        </div>
      </div>
    </div>
  );
}

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

  const location = useLocation();

  const [searchInput, setSearchInput] = useState(query);

  // Zustand 中的 query 变化时，同步到本地输入框
  useEffect(() => {
    setSearchInput(query);
  }, [query]);

  // 从 URL ?q= 参数同步搜索内容（用于标签页等跳转）
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlQuery = params.get('q');
    if (urlQuery) {
      const decoded = decodeURIComponent(urlQuery);
      setSearchInput(decoded);
      setQuery(decoded);
    }
  }, [location.search, setQuery]);

  const [showOnboarding, setShowOnboarding] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [timeFrom, setTimeFrom] = useState('');
  const [timeTo, setTimeTo] = useState('');
  const [openMode, setOpenMode] = useState<'app' | 'web'>('app');
  const [previewThread, setPreviewThread] = useState<Thread | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [mergedThreads, setMergedThreads] = useState<Thread[]>([]);
  const { settings, updateSettings } = useSettings();
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // 首次访问引导：仅在本设备第一次访问时展示
  useEffect(() => {
    try {
      const seen = localStorage.getItem('od_onboarding_seen');
      if (!seen) {
        setShowOnboarding(true);
      }
    } catch (error) {
      console.error('Failed to read onboarding flag:', error);
    }
  }, []);

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

  // 基于查询字符串解析出 token（标签 / 作者）与纯文本关键字
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

  // 使用真实API获取搜索结果
  const { data: searchData, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['search', query, selectedChannel, includedTags, excludedTags, tagLogic, sortMethod, page, perPage, timeFrom, timeTo],
    queryFn: () =>
      searchApi.search({
        query: keywordQuery || undefined,
        channel_ids: selectedChannel ? [selectedChannel] : undefined,
        include_tags: Array.from(new Set([...includedTags, ...tokenIncludeTags])),
        exclude_tags: excludedTags,
        tag_logic: tagLogic,
        // 与 SearchParams.sort_method 对齐：relevance / last_active_desc / created_desc / reply_desc / reaction_desc
        sort_method: sortMethod,
        limit: perPage,
        offset: (page - 1) * perPage,
        created_after: timeFrom || undefined,
        created_before: timeTo || undefined,
        author_name: authorNameFromToken,
      }),
    enabled: true, // 确保即使 queryKey 中有 null/undefined 也执行查询
    staleTime: 30 * 1000, // 30秒
  });

  // 从API响应中提取数据（与后端 SearchResponse.results 对齐）
  const threads = searchData?.results || [];
  const totalResults = searchData?.total || 0;
  const availableTags = searchData?.available_tags || [];
  const totalPages = Math.ceil(totalResults / perPage);

  // 合并多页搜索结果，实现无缝滚动
  useEffect(() => {
    if (!searchData) {
      if (page === 1) {
        setMergedThreads([]);
      }
      return;
    }

    const currentThreads = searchData.results || [];

    if (page === 1) {
      setMergedThreads(currentThreads);
      return;
    }

    setMergedThreads((prev) => {
      if (!prev || prev.length === 0) {
        return currentThreads;
      }
      const existingIds = new Set(prev.map((t) => t.thread_id));
      const newThreads = currentThreads.filter((t) => !existingIds.has(t.thread_id));
      return [...prev, ...newThreads];
    });
  }, [searchData, page]);

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

  // 使用 IntersectionObserver 实现无缝滚动加载
  useEffect(() => {
    const currentRef = loadMoreRef.current;
    if (!currentRef) return;
    if (isLoading || isError || isFetching) return;
    if (page >= totalPages) return;
    if (mergedThreads.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // 只在元素可见且不在加载状态时触发
        if (entries[0].isIntersecting && !isFetching && page < totalPages) {
          setPage(page + 1);
        }
      },
      { threshold: 0.1, rootMargin: '200px' }
    );

    observer.observe(currentRef);
    return () => {
      observer.disconnect();
    };
  }, [isLoading, isError, isFetching, page, totalPages, mergedThreads.length, setPage]);

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

  // 处理标签点击 - 从卡片点击时添加到搜索框
  const handleTagClick = (tag: string) => {
    const newQuery = addToken(searchInput, 'tag', tag);
    setSearchInput(newQuery);
    setQuery(newQuery);
    toast.success(`已添加标签：${tag}`, {
      duration: 2000,
    });
  };

  // 处理高级面板中的标签点击 - 用于筛选
  const handleFilterTagClick = (tag: string) => {
    toggleTag(tag);
  };

  // 关闭预览浮层
  const handleClosePreview = () => {
    setPreviewThread(null);
  };

  const handleCloseOnboarding = () => {
    try {
      localStorage.setItem('od_onboarding_seen', '1');
    } catch (error) {
      console.error('Failed to save onboarding flag:', error);
    }
    setShowOnboarding(false);
  };

  // 频道名称（暂时简化）
  const currentChannelName = selectedChannel || '全频道搜索';

  // 是否有活动的筛选条件
  const hasActiveFilters = query || selectedChannel || tagStates.size > 0 || timeFrom || timeTo;

  return (
    <div className="flex min-h-screen bg-[var(--od-bg)]">
      {/* 回到顶部按钮 */}
      <ScrollToTop />
      {/* 侧边栏（支持移动端开关 + PC 折叠） */}
      <ResizableSidebar
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
      >
        <AppSidebar />
      </ResizableSidebar>

      {/* 主内容区：根据侧边栏折叠状态调整左侧留白（PC 端） */}
      <main
        className={`flex-1 bg-[var(--od-bg)] pb-20 transition-all duration-300 ${
          isSidebarCollapsed ? 'lg:ml-0' : 'lg:ml-[240px]'
        }`}
      >
        {/* 顶部搜索栏 - 集成高级搜索面板 */}
        <TopBar
          searchValue={searchInput}
          onSearchChange={setSearchInput}
          onSearch={handleSearch}
          onMenuClick={() => setIsMobileOpen(true)}
          onQuickSearch={handleQuickSearch}
          searchInputRef={searchInputRef}
          onSelectHistory={handleSelectHistory}
          timeFrom={timeFrom}
          timeTo={timeTo}
          sortMethod={sortMethod}
          tagLogic={tagLogic}
          tagMode={tagMode}
          availableTags={availableTags}
          tagStates={tagStates}
          onTimeFromChange={setTimeFrom}
          onTimeToChange={setTimeTo}
          onSortMethodChange={(value) => setSortMethod(value as any)}
          onTagLogicChange={setTagLogic}
          onTagModeChange={setTagMode}
          onTagClick={handleFilterTagClick}
          onClearAllTags={clearAllTags}
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

        {/* 主页面固定的高级搜索面板 - Banner 下方 */}
        <MainAdvancedPanel
          timeFrom={timeFrom}
          timeTo={timeTo}
          sortMethod={sortMethod}
          tagLogic={tagLogic}
          tagMode={tagMode}
          availableTags={availableTags}
          tagStates={tagStates}
          onTimeFromChange={setTimeFrom}
          onTimeToChange={setTimeTo}
          onSortMethodChange={(value) => setSortMethod(value as any)}
          onTagLogicChange={setTagLogic}
          onTagModeChange={setTagMode}
          onTagClick={handleFilterTagClick}
          onClearAllTags={clearAllTags}
        />

        {/* 搜索结果 */}
        <div className="p-4">
          {/* 统计信息栏 - 显示页数信息 */}
          <div className="animate-in fade-in duration-300">
            <StatsBar
              totalCount={totalResults}
              perPage={perPage}
              openMode={openMode}
              layoutMode={settings.layoutMode}
              currentPage={page}
              totalPages={totalPages}
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

          {/* 搜索结果列表 */}
          {isLoading ? (
            <div
              className={
                settings.layoutMode === 'list'
                  ? 'space-y-4 animate-in fade-in duration-300'
                  : 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-in fade-in duration-300'
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
            <div
              className={
                settings.layoutMode === 'list'
                  ? 'space-y-4 animate-in fade-in duration-300'
                  : 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-in fade-in duration-300'
              }
            >
              {mergedThreads.map((thread) =>
                settings.layoutMode === 'list' ? (
                  <ThreadListItem
                    key={thread.thread_id}
                    thread={thread}
                    onTagClick={handleTagClick}
                    searchQuery={query}
                    onAuthorClick={(authorName) => {
                      const newQuery = addToken(searchInput, 'author', authorName);
                      setSearchInput(newQuery);
                      setQuery(newQuery);
                      toast.success(`已添加作者：${authorName}`, {
                        duration: 2000,
                      });
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
                      setSearchInput(newQuery);
                      setQuery(newQuery);
                      toast.success(`已添加作者：${authorName}`, {
                        duration: 2000,
                      });
                    }}
                    onPreview={setPreviewThread}
                  />
                )
              )}
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
      </main>
      {/* 预览浮层：选中的卡片会上浮居中放大，带淡入/缩放过渡动画，正文支持 Markdown 和独立滚动 */}
      {previewThread && (
        <ThreadPreviewOverlay thread={previewThread} onClose={handleClosePreview} />
      )}

      {/* 首次访问引导浮层 */}
      {showOnboarding && (
        <SearchOnboardingOverlay onClose={handleCloseOnboarding} />
      )}
    </div>
  );
}
