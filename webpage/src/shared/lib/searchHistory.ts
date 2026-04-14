const SEARCH_HISTORY_KEY = 'odysseia_search_history';
const MAX_HISTORY_ITEMS = 20;

export interface SearchHistoryItem {
  id: string;
  query: string;
  timestamp: number;
  channel?: string | null;
  sortMethod?: string;
  tagLogic?: 'and' | 'or';
  includeTags?: string[];
  excludeTags?: string[];
}

export interface SearchHistoryPayload {
  query: string;
  channel?: string | null;
  sortMethod?: string;
  tagLogic?: 'and' | 'or';
  includeTags?: string[];
  excludeTags?: string[];
}

function normalizeStringArray(values?: string[]) {
  return Array.from(new Set((values || []).map((item) => item.trim()).filter(Boolean))).sort();
}

function buildSearchHistoryId(payload: SearchHistoryPayload) {
  const normalizedQuery = payload.query.trim();
  const normalizedChannel = payload.channel?.trim() || '';
  const normalizedSort = payload.sortMethod?.trim() || 'last_active_desc';
  const normalizedTagLogic = payload.tagLogic === 'or' ? 'or' : 'and';
  const normalizedInclude = normalizeStringArray(payload.includeTags).join(',');
  const normalizedExclude = normalizeStringArray(payload.excludeTags).join(',');

  return [normalizedQuery, normalizedChannel, normalizedSort, normalizedTagLogic, normalizedInclude, normalizedExclude].join('::');
}

function normalizeHistoryItem(raw: unknown): SearchHistoryItem | null {
  if (!raw || typeof raw !== 'object') return null;

  const record = raw as Record<string, unknown>;
  const query = typeof record.query === 'string' ? record.query.trim() : '';
  if (!query) return null;

  const channel = typeof record.channel === 'string' && record.channel.trim() ? record.channel.trim() : null;
  const sortMethod = typeof record.sortMethod === 'string' && record.sortMethod.trim()
    ? record.sortMethod.trim()
    : 'last_active_desc';
  const tagLogic = record.tagLogic === 'or' ? 'or' : 'and';
  const includeTags = Array.isArray(record.includeTags)
    ? normalizeStringArray(record.includeTags.filter((item): item is string => typeof item === 'string'))
    : [];
  const excludeTags = Array.isArray(record.excludeTags)
    ? normalizeStringArray(record.excludeTags.filter((item): item is string => typeof item === 'string'))
    : [];
  const timestamp = typeof record.timestamp === 'number' && Number.isFinite(record.timestamp)
    ? record.timestamp
    : Date.now();

  const payload: SearchHistoryPayload = {
    query,
    channel,
    sortMethod,
    tagLogic,
    includeTags,
    excludeTags,
  };

  return {
    id: typeof record.id === 'string' && record.id.trim() ? record.id : buildSearchHistoryId(payload),
    query,
    timestamp,
    channel,
    sortMethod,
    tagLogic,
    includeTags,
    excludeTags,
  };
}

function saveHistory(history: SearchHistoryItem[]) {
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history));
}

export function getSearchHistory(): SearchHistoryItem[] {
  try {
    const history = localStorage.getItem(SEARCH_HISTORY_KEY);
    if (!history) return [];

    const parsed = JSON.parse(history);
    if (!Array.isArray(parsed)) return [];

    return parsed
      .map((item) => normalizeHistoryItem(item))
      .filter((item): item is SearchHistoryItem => Boolean(item))
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, MAX_HISTORY_ITEMS);
  } catch (error) {
    console.error('Failed to load search history:', error);
    return [];
  }
}

export function addSearchHistory(payloadOrQuery: SearchHistoryPayload | string): void {
  const payload = typeof payloadOrQuery === 'string' ? { query: payloadOrQuery } : payloadOrQuery;
  if (!payload.query.trim()) return;

  try {
    const history = getSearchHistory();
    const item: SearchHistoryItem = {
      id: buildSearchHistoryId(payload),
      query: payload.query.trim(),
      timestamp: Date.now(),
      channel: payload.channel?.trim() || null,
      sortMethod: payload.sortMethod?.trim() || 'last_active_desc',
      tagLogic: payload.tagLogic === 'or' ? 'or' : 'and',
      includeTags: normalizeStringArray(payload.includeTags),
      excludeTags: normalizeStringArray(payload.excludeTags),
    };

    const filtered = history.filter((historyItem) => historyItem.id !== item.id);
    saveHistory([item, ...filtered].slice(0, MAX_HISTORY_ITEMS));
  } catch (error) {
    console.error('Failed to save search history:', error);
  }
}

export function removeSearchHistory(itemOrQuery: SearchHistoryItem | string): void {
  try {
    const history = getSearchHistory();
    const filtered = typeof itemOrQuery === 'string'
      ? history.filter((item) => item.id !== itemOrQuery && item.query !== itemOrQuery)
      : history.filter((item) => item.id !== itemOrQuery.id);
    saveHistory(filtered);
  } catch (error) {
    console.error('Failed to remove search history:', error);
  }
}

export function clearSearchHistory(): void {
  try {
    localStorage.removeItem(SEARCH_HISTORY_KEY);
  } catch (error) {
    console.error('Failed to clear search history:', error);
  }
}

export function describeSearchHistoryContext(item: SearchHistoryItem) {
  const parts: string[] = [];

  if (item.channel) parts.push(`频道 ${item.channel}`);
  if (item.sortMethod && item.sortMethod !== 'last_active_desc') parts.push(`排序已调整`);
  if ((item.includeTags?.length || 0) > 0) parts.push(`含 ${item.includeTags!.length} 个标签`);
  if ((item.excludeTags?.length || 0) > 0) parts.push(`排除 ${item.excludeTags!.length} 个标签`);

  return parts.join(' · ');
}
