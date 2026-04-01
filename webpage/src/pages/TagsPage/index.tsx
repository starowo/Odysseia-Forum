import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Tag as TagIcon, TrendingUp, Hash } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { searchApi } from '@/features/search/api/searchApi';
import { addToken } from '@/shared/lib/searchTokenizer';
import { useSettings } from '@/shared/hooks/useSettings';

interface TagWithCount {
  key: string;
  name: string;
  channelId: string;
  channelName: string;
  isVirtual: boolean;
  count: number;
}

const TAG_COUNT_BATCH_SIZE = 8;
const ALL_CHANNELS_VALUE = '__all__';

export function TagsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChannelId, setSelectedChannelId] = useState<string>(ALL_CHANNELS_VALUE);
  const navigate = useNavigate();
  const { settings } = useSettings();

  // 全频道标签源（兼容没有 /meta/channels 的后端）
  const { data: channelTagCatalog = [], isLoading: isCatalogLoading } = useQuery({
    queryKey: ['tags-overview', 'channel-tag-catalog'],
    queryFn: () => searchApi.getChannelTagCatalog(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const channelOptions = useMemo(() => {
    return channelTagCatalog
      .filter((channel) => (channel.available_tags?.length || 0) > 0 || (channel.virtual_tags?.length || 0) > 0)
      .map((channel) => ({
        id: channel.channel_id,
        name: channel.channel_name,
      }))
      .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
  }, [channelTagCatalog]);

  const scopedTagEntries = useMemo(() => {
    const entries: Array<{
      key: string;
      name: string;
      channelId: string;
      channelName: string;
      isVirtual: boolean;
    }> = [];

    for (const channel of channelTagCatalog) {
      if (
        selectedChannelId !== ALL_CHANNELS_VALUE
        && channel.channel_id !== selectedChannelId
      ) {
        continue;
      }

      const virtualSet = new Set((channel.virtual_tags || []).map((tag) => tag.trim()).filter(Boolean));
      const realTags = (channel.available_tags || [])
        .map((tag) => tag.trim())
        .filter((tag) => Boolean(tag) && !virtualSet.has(tag));

      for (const tag of realTags) {
        entries.push({
          key: `${channel.channel_id}::real::${tag}`,
          name: tag,
          channelId: channel.channel_id,
          channelName: channel.channel_name,
          isVirtual: false,
        });
      }

      for (const tag of virtualSet) {
        entries.push({
          key: `${channel.channel_id}::virtual::${tag}`,
          name: tag,
          channelId: channel.channel_id,
          channelName: channel.channel_name,
          isVirtual: true,
        });
      }
    }

    return entries;
  }, [channelTagCatalog, selectedChannelId]);

  // 当前频道范围内总帖子数
  const { data: scopedSearchData, isLoading: isScopedSearchLoading } = useQuery({
    queryKey: ['tags-overview', 'total-threads', selectedChannelId],
    queryFn: () =>
      searchApi.search({
        limit: 1,
        channel_ids:
          selectedChannelId === ALL_CHANNELS_VALUE ? undefined : [selectedChannelId],
      }),
    staleTime: 60 * 1000,
  });

  // 获取每个标签的帖子数量
  const { data: tagCounts } = useQuery({
    queryKey: ['tag-counts', selectedChannelId, scopedTagEntries.map((tag) => tag.key)],
    queryFn: async () => {
      const counts: Record<string, number> = {};

      // 分批并发，避免一次性请求过多导致 429/超时
      for (let i = 0; i < scopedTagEntries.length; i += TAG_COUNT_BATCH_SIZE) {
        const batch = scopedTagEntries.slice(i, i + TAG_COUNT_BATCH_SIZE);
        const batchEntries = await Promise.all(
          batch.map(async (tagEntry) => {
            if (tagEntry.isVirtual) {
              return [tagEntry.key, 0] as const;
            }

            try {
              const result = await searchApi.search({
                include_tags: [tagEntry.name],
                channel_ids:
                  selectedChannelId === ALL_CHANNELS_VALUE ? undefined : [tagEntry.channelId],
                limit: 1,
              });
              return [tagEntry.key, result.total] as const;
            } catch (error) {
              console.error(`Failed to fetch count for tag: ${tagEntry.name}`, error);
              return [tagEntry.key, 0] as const;
            }
          }),
        );

        for (const [tag, count] of batchEntries) {
          counts[tag] = count;
        }
      }

      return counts;
    },
    enabled: scopedTagEntries.length > 0,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  // 组合标签和数量
  const tagsWithCounts: TagWithCount[] = useMemo(() => {
    return scopedTagEntries
      .map((tagEntry) => ({
        key: tagEntry.key,
        name: tagEntry.name,
        channelId: tagEntry.channelId,
        channelName: tagEntry.channelName,
        isVirtual: tagEntry.isVirtual,
        count: tagCounts?.[tagEntry.key] || 0,
      }))
      .sort((a, b) => b.count - a.count); // 按数量降序排序
  }, [scopedTagEntries, tagCounts]);

  // 过滤标签
  const filteredTags = useMemo(() => {
    if (!searchQuery.trim()) return tagsWithCounts;

    const query = searchQuery.toLowerCase();
    return tagsWithCounts.filter((tag) =>
      tag.name.toLowerCase().includes(query) || tag.channelName.toLowerCase().includes(query)
    );
  }, [tagsWithCounts, searchQuery]);

  // 点击标签跳转到搜索页（使用统一的 token 语法生成）
  const handleTagClick = (tag: TagWithCount) => {
    let query = addToken('', 'tag', tag.name);
    query = addToken(query, 'channel', tag.channelId);
    navigate(`/?q=${encodeURIComponent(query)}`);
  };

  // 统计信息
  const totalTags = new Set(scopedTagEntries.map((tag) => tag.name)).size;
  const totalThreads = Number(scopedSearchData?.total || 0);
  const isPageLoading = isCatalogLoading || isScopedSearchLoading;

  return (
    <>
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
                    <p className="text-sm text-[var(--od-text-secondary)]">平均帖子/每标签</p>
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
              <div className="grid grid-cols-1 gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
                <select
                  value={selectedChannelId}
                  onChange={(e) => setSelectedChannelId(e.target.value)}
                  className="rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] px-3 py-3 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
                >
                  <option value={ALL_CHANNELS_VALUE}>全部频道</option>
                  {channelOptions.map((channel) => (
                    <option key={channel.id} value={channel.id}>
                      {channel.name}
                    </option>
                  ))}
                </select>
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
            </div>

            {/* 标签网格 */}
            {isPageLoading ? (
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
                    key={tag.key}
                    onClick={() => handleTagClick(tag)}
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
                          <h3 className="truncate font-semibold text-[var(--od-text-primary)] transition-colors group-hover:text-[var(--od-accent)]">
                            {tag.name}
                          </h3>
                          {tag.isVirtual && (
                            <span className="rounded-full border border-[var(--od-accent)]/30 bg-[var(--od-accent)]/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--od-accent)]">
                              虚拟
                            </span>
                          )}
                        </div>
                        <p className="truncate text-xs text-[var(--od-text-tertiary)]">
                          频道：{tag.channelName}
                        </p>
                        <p className="mt-1 text-sm text-[var(--od-text-secondary)]">
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
                            (tag.count / Math.max(...filteredTags.map((t) => t.count), 1)) * 100,
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
    </>
  );
}
