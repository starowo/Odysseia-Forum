import type { SearchParams } from '@/features/search/hooks/useSearchParams';

export const searchKeys = {
  all: ['search'] as const,
  results: (params: SearchParams & {
    effectiveChannelIds?: string[];
    effectiveIncludeTags: string[];
    effectiveExcludeTags: string[];
    effectiveSortMethod?: string;
    effectivePerPage: number;
    preferenceSignature?: string;
  }) => [
    ...searchKeys.all,
    'results',
    {
      query: params.query,
      channel: params.channel,
      effectiveChannelIds: params.effectiveChannelIds ?? [],
      effectiveIncludeTags: params.effectiveIncludeTags,
      effectiveExcludeTags: params.effectiveExcludeTags,
      includeAuthors: params.includeAuthors,
      excludeAuthors: params.excludeAuthors,
      tagLogic: params.tagLogic,
      effectiveSortMethod: params.effectiveSortMethod,
      effectivePerPage: params.effectivePerPage,
      timeFrom: params.timeFrom,
      timeTo: params.timeTo,
      preferenceSignature: params.preferenceSignature ?? 'no-preferences',
    },
  ] as const,
  filterMeta: (channelId: string | null) => [...searchKeys.all, 'filter-meta', { channelId }] as const,
  channelTagCatalog: () => [...searchKeys.all, 'channel-tag-catalog'] as const,
  suggestions: (params: {
    query: string;
    channel: string | null;
    preferenceSignature?: string;
    channelIds?: string[];
    includeTags?: string[];
    excludeTags?: string[];
  }) => [
    ...searchKeys.all,
    'suggestions',
    {
      query: params.query,
      channel: params.channel,
      preferenceSignature: params.preferenceSignature ?? 'no-preferences',
      channelIds: params.channelIds ?? [],
      includeTags: params.includeTags ?? [],
      excludeTags: params.excludeTags ?? [],
    },
  ] as const,
  drawPool: (params: {
    preferenceSignature: string;
    scopeMode: string;
    selectedChannelId: string;
    effectiveChannelIds?: string[];
  }) => [
    ...searchKeys.all,
    'draw-pool',
    {
      preferenceSignature: params.preferenceSignature,
      scopeMode: params.scopeMode,
      selectedChannelId: params.selectedChannelId,
      effectiveChannelIds: params.effectiveChannelIds ?? [],
    },
  ] as const,
  thread: (threadId: string | null) => [...searchKeys.all, 'thread', threadId] as const,
};
