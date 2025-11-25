import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Tag as TagIcon, TrendingUp, Hash } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout/MainLayout';
import { searchApi } from '@/features/search/api/searchApi';
import { addToken } from '@/lib/searchTokenizer';
import { useSettings } from '@/hooks/useSettings';

interface TagWithCount {
  name: string;
  count: number;
}

export function TagsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();
  const { settings } = useSettings();

  // 获取所有频道及其标签
  const { data: channels, isLoading } = useQuery({
    queryKey: ['meta', 'channels'],
    queryFn: searchApi.getChannels,
    staleTime: 5 * 60 * 1000,
  });

  // 聚合所有标签
  const availableTags = useMemo(() => {
    if (!channels) return [];
    const tags = new Set<string>();
    channels.forEach((ch) => {
      ch.tags?.forEach((t) => tags.add(t.name));
    });
    return Array.from(tags);
  }, [channels]);

  // 获取每个标签的帖子数量
  const { data: tagCounts } = useQuery({
    queryKey: ['tag-counts', availableTags],
    queryFn: async () => {
      const counts: Record<string, number> = {};

      // 并行获取所有标签的数量
      await Promise.all(
        availableTags.map(async (tag) => {
          try {
            const result = await searchApi.search({
              include_tags: [tag],
              limit: 1,
            });
            counts[tag] = result.total;
          } catch (error) {
            console.error(`Failed to fetch count for tag: ${tag}`, error);
            counts[tag] = 0;
          }
        })
      );

      return counts;
    },
    enabled: availableTags.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  // 组合标签和数量
  const tagsWithCounts: TagWithCount[] = useMemo(() => {
    if (!tagCounts) return [];

    return availableTags
      .map((tag) => ({
        name: tag,
        count: tagCounts[tag] || 0,
      }))
      .sort((a, b) => b.count - a.count); // 按数量降序排序
  }, [availableTags, tagCounts]);

  // 过滤标签
  const filteredTags = useMemo(() => {
    if (!searchQuery.trim()) return tagsWithCounts;

    const query = searchQuery.toLowerCase();
    return tagsWithCounts.filter((tag) =>
      tag.name.toLowerCase().includes(query)
    );
  }, [tagsWithCounts, searchQuery]);

  // 点击标签跳转到搜索页（使用统一的 token 语法生成）
  const handleTagClick = (tagName: string) => {
    const query = addToken('', 'tag', tagName);
    navigate(`/?q=${encodeURIComponent(query)}`);
  };

  // 统计信息
  const totalTags = tagsWithCounts.length;
  const totalThreads = tagsWithCounts.reduce((sum, tag) => sum + tag.count, 0);

  return (
    <MainLayout>
      <div className="bg-[var(--od-bg)] text-[var(--od-text-primary)]">
        {/* 标题栏 */}
        <div className="border-b border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TagIcon className="h-6 w-6 text-[var(--od-accent)]" />
              <div>
                <h1 className="text-xl font-bold text-[var(--od-text-primary)]">标签总览</h1>
                <p className="text-sm text-[var(--od-text-secondary)]">
                  探索所有可用标签，发现感兴趣的内容
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="hidden rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-1.5 text-xs font-medium text-[var(--od-text-secondary)] transition-all duration-200 hover:border-[var(--od-accent)] hover:text-[var(--od-text-primary)] sm:inline-flex"
            >
              返回搜索
            </button>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            {/* 统计卡片 */}
            <div
              className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-in fade-in slide-in-from-top-4 duration-500"
              style={{ animationDelay: '100ms' }}
            >
              <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-5 shadow-sm transition-all duration-200 hover:shadow-md">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--od-text-secondary)]">标签总数</p>
                    <p className="mt-1 text-3xl font-bold text-[var(--od-text-primary)]">{totalTags}</p>
                  </div>
                  <Hash className="h-10 w-10 text-[var(--od-accent)]/20" />
                </div>
              </div>

              <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-5 shadow-sm transition-all duration-200 hover:shadow-md">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--od-text-secondary)]">相关帖子</p>
                    <p className="mt-1 text-3xl font-bold text-[var(--od-text-primary)]">{totalThreads}</p>
                  </div>
                  <TrendingUp className="h-10 w-10 text-green-500/20" />
                </div>
              </div>

              <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-5 shadow-sm transition-all duration-200 hover:shadow-md sm:col-span-2 lg:col-span-1">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[var(--od-text-secondary)]">平均每标签</p>
                    <p className="mt-1 text-3xl font-bold text-[var(--od-text-primary)]">
                      {totalTags > 0 ? Math.round(totalThreads / totalTags) : 0}
                    </p>
                  </div>
                  <TagIcon className="h-10 w-10 text-blue-500/20" />
                </div>
              </div>
            </div>

            {/* 搜索框 */}
            <div
              className="mb-6 animate-in fade-in slide-in-from-top-4 duration-500"
              style={{ animationDelay: '200ms' }}
            >
              <div className="relative">
                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--od-text-tertiary)]" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索标签..."
                  className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] py-3 pl-12 pr-4 text-[var(--od-text-primary)] placeholder:text-[var(--od-text-tertiary)] focus:border-[var(--od-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]/20"
                />
              </div>
            </div>

            {/* 标签网格 */}
            {isLoading ? (
              <div className={`grid grid-cols-1 gap-3 sm:grid-cols-2 ${settings.sidebarCollapsed ? 'lg:grid-cols-4 xl:grid-cols-5' : 'lg:grid-cols-3 xl:grid-cols-4'}`}>
                {Array.from({ length: 12 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-24 animate-pulse rounded-lg border border-[var(--od-border)] bg-[var(--od-card)]"
                  />
                ))}
              </div>
            ) : filteredTags.length > 0 ? (
              <div
                className={`grid grid-cols-1 gap-3 sm:grid-cols-2 ${settings.sidebarCollapsed ? 'lg:grid-cols-4 xl:grid-cols-5' : 'lg:grid-cols-3 xl:grid-cols-4'} animate-in fade-in duration-500`}
                style={{ animationDelay: '300ms' }}
              >
                {filteredTags.map((tag, index) => (
                  <button
                    key={tag.name}
                    onClick={() => handleTagClick(tag.name)}
                    className="group relative overflow-hidden rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] p-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-[var(--od-accent)] hover:shadow-md"
                    style={{
                      animationDelay: `${300 + index * 30}ms`,
                    }}
                  >
                    {/* 背景渐变效果 */}
                    <div className="absolute inset-0 bg-gradient-to-br from-[var(--od-accent)]/0 to-[var(--od-accent)]/0 transition-all duration-300 group-hover:from-[var(--od-accent)]/5 group-hover:to-[var(--od-accent)]/10" />

                    <div className="relative flex items-start justify-between">
                      <div className="flex-1 overflow-hidden">
                        <div className="mb-2 flex items-center gap-2">
                          <TagIcon className="h-4 w-4 flex-shrink-0 text-[var(--od-accent)]" />
                          <h3 className="truncate font-semibold text-[var(--od-text-primary)] transition-colors group-hover:text-[var(--od-accent)]">
                            {tag.name}
                          </h3>
                        </div>
                        <p className="text-sm text-[var(--od-text-secondary)]">
                          {tag.count} 个帖子
                        </p>
                      </div>

                      {/* 数量徽章 */}
                      <div className="ml-2 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-[var(--od-accent)]/10 text-sm font-bold text-[var(--od-accent)] transition-all duration-200 group-hover:bg-[var(--od-accent)] group-hover:text-white">
                        {tag.count}
                      </div>
                    </div>

                    {/* 热度指示条 */}
                    <div className="relative mt-3 h-1 overflow-hidden rounded-full bg-[var(--od-bg-tertiary)]">
                      <div
                        className="h-full bg-gradient-to-r from-[var(--od-accent)]/50 to-[var(--od-accent)] transition-all duration-500"
                        style={{
                          width: `${Math.min(
                            (tag.count / Math.max(...filteredTags.map((t) => t.count))) * 100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] p-8">
                <div className="text-center">
                  <Search className="mx-auto mb-4 h-16 w-16 text-[var(--od-text-tertiary)]" />
                  <h3 className="mb-2 text-xl font-bold text-[var(--od-text-primary)]">
                    未找到匹配的标签
                  </h3>
                  <p className="text-[var(--od-text-secondary)]">
                    尝试使用其他关键词搜索
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}