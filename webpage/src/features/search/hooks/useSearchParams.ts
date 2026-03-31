/**
 * useSearchParams — 搜索参数的 URL 协议层
 *
 * 所有搜索条件以 URL searchParams 为单一数据来源 (Single Source of Truth)。
 * 本 Hook 负责：
 *   1. 从 URL 解析出类型安全的搜索参数
 *   2. 提供更新函数，将新参数序列化回 URL
 *   3. 每次参数变化时自动重置 page 到 1（通过返回值让页面自行管理）
 *
 * URL 参数协议：
 *   q           → 关键词
 *   channel     → 频道 ID
 *   sort        → 排序方式
 *   tags        → 包含标签 (逗号分隔)
 *   exclude     → 排除标签 (逗号分隔)
 *   tag_logic   → 标签逻辑 (and | or)
 *   time_from   → 时间下限
 *   time_to     → 时间上限
 */

import { useSearchParams as useRouterSearchParams } from 'react-router-dom';
import { useCallback, useMemo } from 'react';

export type SortMethod =
  | 'relevance'
  | 'last_active_desc'
  | 'created_desc'
  | 'reply_desc'
  | 'reaction_desc';

export type TagLogic = 'and' | 'or';

/** 从 URL 解析后的搜索参数结构 */
export interface SearchParams {
  query: string;
  channel: string | null;
  sortMethod: SortMethod;
  includeTags: string[];
  excludeTags: string[];
  tagLogic: TagLogic;
  timeFrom: string;
  timeTo: string;
}

/** 合法的排序值集合，用于校验 */
const VALID_SORT_METHODS: Set<string> = new Set([
  'relevance',
  'last_active_desc',
  'created_desc',
  'reply_desc',
  'reaction_desc',
]);

/**
 * 从 URL searchParams 解析搜索参数。
 * 对于缺失或非法的值，回退到默认值。
 */
export function parseParams(sp: URLSearchParams): SearchParams {
  const rawSort = sp.get('sort') || 'last_active_desc';
  const sortMethod: SortMethod = VALID_SORT_METHODS.has(rawSort)
    ? (rawSort as SortMethod)
    : 'last_active_desc';

  const rawTagLogic = sp.get('tag_logic');
  const tagLogic: TagLogic = rawTagLogic === 'or' ? 'or' : 'and';

  const rawTags = sp.get('tags');
  const includeTags = rawTags ? rawTags.split(',').filter(Boolean) : [];

  const rawExclude = sp.get('exclude');
  const excludeTags = rawExclude ? rawExclude.split(',').filter(Boolean) : [];

  return {
    query: sp.get('q') || '',
    channel: sp.get('channel') || null,
    sortMethod,
    includeTags,
    excludeTags,
    tagLogic,
    timeFrom: sp.get('time_from') || '',
    timeTo: sp.get('time_to') || '',
  };
}

/**
 * 将搜索参数序列化为 URLSearchParams。
 * 空值 / 默认值不写入 URL，保持 URL 简洁。
 */
export function serializeParams(params: Partial<SearchParams>): URLSearchParams {
  const sp = new URLSearchParams();

  if (params.query) sp.set('q', params.query);
  if (params.channel) sp.set('channel', params.channel);
  if (params.sortMethod && params.sortMethod !== 'last_active_desc') {
    sp.set('sort', params.sortMethod);
  }
  if (params.includeTags && params.includeTags.length > 0) {
    sp.set('tags', params.includeTags.join(','));
  }
  if (params.excludeTags && params.excludeTags.length > 0) {
    sp.set('exclude', params.excludeTags.join(','));
  }
  if (params.tagLogic && params.tagLogic !== 'and') {
    sp.set('tag_logic', params.tagLogic);
  }
  if (params.timeFrom) sp.set('time_from', params.timeFrom);
  if (params.timeTo) sp.set('time_to', params.timeTo);

  return sp;
}

/**
 * 搜索参数 URL 协议 Hook
 *
 * @returns `params` — 当前 URL 中解析出的搜索条件
 * @returns `setParams` — 合并更新搜索参数并写回 URL
 * @returns `clearParams` — 清空所有筛选条件
 */
export function useSearchURLParams() {
  const [searchParams, setSearchParams] = useRouterSearchParams();

  // 解析当前 URL 参数
  const params = useMemo(() => parseParams(searchParams), [searchParams]);

  // 合并更新：只更新传入的字段，其余保持不变
  const setParams = useCallback(
    (updates: Partial<SearchParams>) => {
      const current = parseParams(searchParams);
      const merged = { ...current, ...updates };
      const newSP = serializeParams(merged);
      // replace: true 避免每次筛选都往 history 里堆一条记录
      // 搜索词变化用 push（可回退），筛选微调用 replace
      const isQueryChange = updates.query !== undefined && updates.query !== current.query;
      setSearchParams(newSP, { replace: !isQueryChange });
    },
    [searchParams, setSearchParams],
  );

  // 清空所有筛选
  const clearParams = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  // 判断是否有任何活动筛选
  const hasActiveFilters = useMemo(() => {
    return !!(
      params.query ||
      params.channel ||
      params.includeTags.length > 0 ||
      params.excludeTags.length > 0 ||
      params.timeFrom ||
      params.timeTo
    );
  }, [params]);

  return {
    params,
    setParams,
    clearParams,
    hasActiveFilters,
  } as const;
}
