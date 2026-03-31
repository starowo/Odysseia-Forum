/**
 * [`useSearchParams`](webpage/src/features/search/hooks/useSearchParams.ts:1) — 搜索参数的 URL 协议层
 *
 * 所有搜索条件以 URL searchParams 为单一数据来源。
 * 当前协议以 [`q`](webpage/src/features/search/hooks/useSearchParams.ts:11) 为核心，
 * token 搜索语法负责承载 tag / author 等高级条件，
 * 频道筛选独立使用 [`channel`](webpage/src/features/search/hooks/useSearchParams.ts:25) URL 参数，
 * 面板型筛选继续承载排序与时间范围。
 */

import { migrateLegacySyntax, tokenizeSearchPayload } from '@/shared/lib/searchTokenizer';
import { useCallback, useMemo } from 'react';
import { useSearchParams as useRouterSearchParams } from 'react-router-dom';

export type SortMethod =
  | 'relevance'
  | 'last_active_desc'
  | 'created_desc'
  | 'reply_desc'
  | 'reaction_desc';

export type TagLogic = 'and' | 'or';

export interface SearchParams {
  query: string;
  channel: string | null;
  sortMethod: SortMethod;
  includeTags: string[];
  excludeTags: string[];
  includeAuthors: string[];
  excludeAuthors: string[];
  tagLogic: TagLogic;
  timeFrom: string;
  timeTo: string;
}

const VALID_SORT_METHODS: Set<string> = new Set([
  'relevance',
  'last_active_desc',
  'created_desc',
  'reply_desc',
  'reaction_desc',
]);

function normalizeQuery(rawQuery: string) {
  return migrateLegacySyntax(rawQuery || '').replace(/\s+/g, ' ').trim();
}

function stripChannelTokens(query: string) {
  return normalizeQuery(query)
    .replace(/(^|\s)-?\$channel:[^$]+\$/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function parseParams(sp: URLSearchParams): SearchParams {
  const rawSort = sp.get('sort') || 'last_active_desc';
  const sortMethod: SortMethod = VALID_SORT_METHODS.has(rawSort)
    ? (rawSort as SortMethod)
    : 'last_active_desc';

  const rawTagLogic = sp.get('tag_logic');
  const tagLogic: TagLogic = rawTagLogic === 'or' ? 'or' : 'and';

  const rawQuery = normalizeQuery(sp.get('q') || '');
  const tokenized = tokenizeSearchPayload(rawQuery);
  const query = stripChannelTokens(rawQuery);

  return {
    query,
    channel: sp.get('channel') || tokenized.channels[0] || null,
    sortMethod,
    includeTags: tokenizeSearchPayload(query).includeTags,
    excludeTags: tokenizeSearchPayload(query).excludeTags,
    includeAuthors: tokenizeSearchPayload(query).includeAuthors,
    excludeAuthors: tokenizeSearchPayload(query).excludeAuthors,
    tagLogic,
    timeFrom: sp.get('time_from') || '',
    timeTo: sp.get('time_to') || '',
  };
}

export function serializeParams(params: Partial<SearchParams>): URLSearchParams {
  const sp = new URLSearchParams();

  if (params.query) sp.set('q', normalizeQuery(params.query));
  if (params.channel) sp.set('channel', params.channel);
  if (params.sortMethod && params.sortMethod !== 'last_active_desc') {
    sp.set('sort', params.sortMethod);
  }
  if (params.tagLogic && params.tagLogic !== 'and') {
    sp.set('tag_logic', params.tagLogic);
  }
  if (params.timeFrom) sp.set('time_from', params.timeFrom);
  if (params.timeTo) sp.set('time_to', params.timeTo);

  return sp;
}

export function useSearchURLParams() {
  const [searchParams, setSearchParams] = useRouterSearchParams();

  const params = useMemo(() => parseParams(searchParams), [searchParams]);

  const setParams = useCallback(
    (updates: Partial<SearchParams>) => {
      const current = parseParams(searchParams);
      const merged = { ...current, ...updates };
      const newSP = serializeParams(merged);
      const isQueryChange = updates.query !== undefined && updates.query !== current.query;
      setSearchParams(newSP, { replace: !isQueryChange });
    },
    [searchParams, setSearchParams],
  );

  const clearParams = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  const hasActiveFilters = useMemo(() => {
    return !!(
      params.query ||
      params.channel ||
      params.includeTags.length > 0 ||
      params.excludeTags.length > 0 ||
      params.includeAuthors.length > 0 ||
      params.excludeAuthors.length > 0 ||
      params.timeFrom ||
      params.timeTo ||
      (params.sortMethod && params.sortMethod !== 'last_active_desc') ||
      (params.tagLogic && params.tagLogic !== 'and')
    );
  }, [params]);

  return {
    params,
    setParams,
    clearParams,
    hasActiveFilters,
  } as const;
}
