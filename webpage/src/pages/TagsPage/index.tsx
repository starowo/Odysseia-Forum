import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Tag as TagIcon, TrendingUp, Hash } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { searchApi } from '@/features/search/api/searchApi';
import { searchKeys } from '@/features/search/lib/queryKeys';
import { addToken } from '@/shared/lib/searchTokenizer';
import { useSidebarCollapsedSetting } from '@/shared/hooks/useSettings';
import { FluidDivider } from '@/shared/ui/FluidDivider';

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
  const sidebarCollapsed = useSidebarCollapsedSetting();

  // 全频道标签源（兼容没有 /meta/channels 的后端）
  const { data: channelTagCatalog = [], isLoading: isCatalogLoading } = useQuery({
    queryKey: searchKeys.channelTagCatalog(),
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
    navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  // 统计信息
  const totalTags = new Set(scopedTagEntries.map((tag) => tag.name)).size;
  const totalThreads = Number(scopedSearchData?.total || 0);
  const isPageLoading = isCatalogLoading || isScopedSearchLoading;
  const maxTagCount = Math.max(...filteredTags.map((tag) => tag.count), 1);

  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden text-[var(--od-text-primary)]">
      <div className="animate-in fade-in duration-500 flex-1 p-4 sm:p-6 lg:p-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-10 lg:gap-14">
          <div>
            <FluidDivider label="Tags" tone="strong" className="mb-8 lg:mb-10" />
            <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
                  <TagIcon className="h-5 w-5" />
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--od-text-tertiary)]">
                    标签索引
                  </p>
                  <div className="space-y-1.5">
                    <h1 className="od-section-title">标签总览</h1>
                    <p className="max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)]">
                      浏览当前社区里已经形成讨论的标签脉络，先从主题分布里找到方向，再进入搜索查看具体帖子。
                    </p>
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => navigate('/search')}
                className="od-inline-action od-inline-action-ghost hidden sm:inline-flex"
              >
                返回搜索
              </button>
            </div>

            <div
              className="mt-8 grid grid-cols-1 gap-x-8 gap-y-6 sm:grid-cols-2 lg:mt-10 lg:grid-cols-3 animate-in fade-in slide-in-from-top-4 duration-500"
              style={{ animationDelay: '100ms' }}
            >
              <div className="flex items-start justify-between gap-4 py-2">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-[var(--od-text-secondary)]">标签总数</p>
                  <p className="text-[2rem] font-semibold tracking-tight text-[var(--od-text-value)]">{totalTags}</p>
                  <p className="text-xs leading-5 text-[var(--od-text-tertiary)]">当前筛选范围内可浏览的独立标签。</p>
                </div>
                <Hash className="mt-1 h-8 w-8 text-[var(--od-text-secondary)]/26" />
              </div>

              <div className="flex items-start justify-between gap-4 py-2">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-[var(--od-text-secondary)]">相关帖子</p>
                  <p className="text-[2rem] font-semibold tracking-tight text-[var(--od-text-value)]">{totalThreads}</p>
                  <p className="text-xs leading-5 text-[var(--od-text-tertiary)]">所有命中帖子总量，用来判断主题是否已经成形。</p>
                </div>
                <TrendingUp className="mt-1 h-8 w-8 text-[var(--od-text-secondary)]/26" />
              </div>

              <div className="flex items-start justify-between gap-4 py-2 sm:col-span-2 lg:col-span-1">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-[var(--od-text-secondary)]">平均帖子 / 每标签</p>
                  <p className="text-[2rem] font-semibold tracking-tight text-[var(--od-text-value)]">
                    {totalTags > 0 ? Math.round(totalThreads / totalTags) : 0}
                  </p>
                  <p className="text-xs leading-5 text-[var(--od-text-tertiary)]">粗略感受讨论密度，不作为绝对热度判断。</p>
                </div>
                <TagIcon className="mt-1 h-8 w-8 text-[var(--od-text-secondary)]/26" />
              </div>
            </div>
          </div>

          <section className="px-1">
            <FluidDivider label="Tag Browser" className="mb-8 lg:mb-10" />
            <div className="mb-8 flex items-start gap-4 lg:mb-10">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
                <Search className="h-5 w-5" />
              </div>
              <div className="space-y-1.5">
                <h2 className="od-section-title">筛选标签范围</h2>
                <p className="max-w-3xl text-sm leading-6 text-[var(--od-text-secondary)]">
                  先缩小频道范围，再按名称检索，会更容易找到真正有内容沉淀的标签。
                </p>
              </div>
            </div>

            {/* 搜索框 */}
            <div
              className="animate-in fade-in slide-in-from-top-4 duration-500"
              style={{ animationDelay: '200ms' }}
            >
              <div className="grid grid-cols-1 gap-4 md:grid-cols-[240px_minmax(0,1fr)]">
                <select
                  value={selectedChannelId}
                  onChange={(e) => setSelectedChannelId(e.target.value)}
                  className="rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_70%,transparent)] px-4 py-3.5 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
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
                    className="w-full rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_70%,transparent)] py-3.5 pl-12 pr-4 text-[var(--od-text-primary)] placeholder:text-[var(--od-text-tertiary)] focus:border-[var(--od-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--od-accent)]/16"
                  />
                </div>
              </div>
            </div>
          </section>

            {/* 标签网格 */}
          {isPageLoading ? (
            <div className={`grid grid-cols-1 gap-4 sm:grid-cols-2 lg:gap-5 ${sidebarCollapsed ? 'lg:grid-cols-4 xl:grid-cols-5' : 'lg:grid-cols-3 xl:grid-cols-4'}`}>
                {Array.from({ length: 12 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-24 animate-pulse"
                  />
                ))}
              </div>
            ) : filteredTags.length > 0 ? (
              <div
                className={`grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2 lg:gap-x-10 lg:gap-y-3 ${sidebarCollapsed ? 'lg:grid-cols-4 xl:grid-cols-5' : 'lg:grid-cols-3 xl:grid-cols-4'} animate-in fade-in duration-500`}
                style={{ animationDelay: '300ms' }}
              >
                {filteredTags.map((tag, index) => (
                  <button
                    key={tag.key}
                    onClick={() => handleTagClick(tag)}
                    className="group relative py-4 text-left transition-colors duration-200"
                    style={{
                      animationDelay: `${300 + index * 30}ms`,
                    }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 overflow-hidden">
                        <div className="mb-2 flex items-center gap-2.5">
                          <h3 className="truncate text-[1.02rem] font-semibold tracking-tight text-[var(--od-text-primary)] transition-colors group-hover:text-[var(--od-accent)]">
                            {tag.name}
                          </h3>
                          {tag.isVirtual && (
                            <span className="rounded-full border border-[var(--od-accent)]/30 bg-[var(--od-accent)]/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--od-accent)]">
                              虚拟
                            </span>
                          )}
                        </div>
                        <p className="truncate text-xs tracking-[0.02em] text-[var(--od-text-tertiary)]">
                          频道 <span className="text-[var(--od-text-secondary)]">{tag.channelName}</span>
                        </p>
                        <p className="mt-2 text-sm text-[var(--od-text-secondary)] transition-colors group-hover:text-[var(--od-text-primary)]">
                          {tag.count} 个帖子
                        </p>
                      </div>

                      <div className="flex min-w-[2.75rem] flex-shrink-0 items-baseline justify-end text-right">
                        <span className="text-lg font-semibold tracking-tight text-[var(--od-accent)] transition-colors group-hover:text-[var(--od-accent)]">
                          {tag.count}
                        </span>
                      </div>
                    </div>

                    <div className="relative mt-4 h-[2px] overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--od-text-secondary)_10%,transparent)]">
                      <div
                        className="h-full bg-gradient-to-r from-[var(--od-accent)]/50 to-[var(--od-accent)] transition-all duration-500"
                        style={{
                          width: `${Math.min((tag.count / maxTagCount) * 100, 100)}%`,
                        }}
                      />
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex min-h-[420px] items-center justify-center p-10">
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
  );
}
