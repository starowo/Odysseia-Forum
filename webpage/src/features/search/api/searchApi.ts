import { SearchParams as ApiSearchParams, SearchResponse, Thread } from '@/entities/thread/types';
import { apiClient } from '@/shared/api/client';
import { CHANNEL_CATEGORIES } from '@/shared/config/navigation';
import { tokenizeSearchPayload } from '@/shared/lib/searchTokenizer';

export type UISortMethod =
  | 'relevance'
  | 'last_active_desc'
  | 'created_desc'
  | 'reply_desc'
  | 'reaction_desc';

export interface SearchUIRequest {
  query?: string;
  channel_ids?: Array<number | string> | null;
  include_tags?: string[];
  exclude_tags?: string[];
  include_authors?: Array<number | string>;
  exclude_authors?: Array<number | string>;
  tag_logic?: 'and' | 'or';
  sort_method?: UISortMethod;
  created_after?: string | null;
  created_before?: string | null;
  active_after?: string | null;
  active_before?: string | null;
  limit?: number;
  offset?: number;
  guild_id?: number;
  search_by_collection?: boolean;
  author_name?: string;
}

export interface SearchSuggestionAuthor {
  id: string;
  name: string;
  avatar_url?: string | null;
}

export interface SearchSuggestionThread {
  thread_id: string;
  title: string;
  snippet?: string | null;
  thumbnail_url?: string | null;
  author_name?: string | null;
  author_avatar_url?: string | null;
  source_thread?: Thread;
}

export interface SearchSuggestionResponse {
  top_authors?: SearchSuggestionAuthor[];
  top_threads?: SearchSuggestionThread[];
  top_tags?: string[];
}

export interface SearchHistoryItem {
  id?: string;
  query: string;
  timestamp: number;
}

export interface ChannelTagCatalogItem {
  channel_id: string;
  channel_name: string;
  available_tags: string[];
  virtual_tags: string[];
}

const DEFAULT_NUMERIC_RANGE = '[0, 10000000)';
const GLOBAL_TAG_DISCOVERY_BATCH_SIZE = 6;

function normalizeIdList(values?: Array<number | string> | null): string[] | null {
  if (!values || values.length === 0) return null;

  const normalized = values
    .map((value) => String(value ?? '').trim())
    .filter((value) => /^\d+$/.test(value));

  return normalized.length > 0 ? Array.from(new Set(normalized)) : null;
}

function toApiIntIdList(values: string[] | null): number[] | null {
  return values as unknown as number[] | null;
}

function mapSortMethod(sortMethod?: UISortMethod): ApiSearchParams['sort_method'] {
  const sortMap: Record<UISortMethod, ApiSearchParams['sort_method']> = {
    relevance: 'comprehensive',
    last_active_desc: 'last_active',
    created_desc: 'created_at',
    reply_desc: 'reply_count',
    reaction_desc: 'reaction_count',
  };

  return sortMap[sortMethod || 'last_active_desc'] || 'last_active';
}

function dedupeStrings(values: Array<string | number | null | undefined>) {
  return Array.from(
    new Set(
      values
        .map((value) => String(value ?? '').trim())
        .filter(Boolean),
    ),
  );
}

function escapeKeywordPhrase(value: string) {
  return value.replace(/"/g, '').trim();
}

function buildKeywordString(text: string, includeAuthorNames: string[]) {
  const keywordParts: string[] = [];

  if (includeAuthorNames.length > 0) {
    // 后端真正识别的是 keywords 里的 author: 语法，
    // 而不是 SearchRequest.author_name 字段。
    // 当前先兼容一个作者 token；多作者精确并集后端暂不支持。
    const primaryAuthor = escapeKeywordPhrase(includeAuthorNames[0]);
    if (primaryAuthor) {
      keywordParts.push(`author:"${primaryAuthor}"`);
    }
  }

  if (text) {
    keywordParts.push(text);
  }

  return keywordParts.join(' ').trim() || null;
}

function buildSearchRequest(params: SearchUIRequest): ApiSearchParams {
  const tokenized = tokenizeSearchPayload(params.query || '');

  const channelIdsFromUrl = normalizeIdList(params.channel_ids);
  const channelIdsFromTokens = normalizeIdList(tokenized.channels);
  const channel_ids = channelIdsFromUrl ?? channelIdsFromTokens;

  const includeAuthorNames = dedupeStrings(tokenized.includeAuthors);
  const includeAuthorIds = normalizeIdList(params.include_authors ?? []);
  const excludeAuthorIds = normalizeIdList(params.exclude_authors ?? []);

  const requestBody: ApiSearchParams = {
    guild_id: params.guild_id,
    channel_ids: toApiIntIdList(channel_ids),
    include_tags: dedupeStrings([...(params.include_tags || []), ...tokenized.includeTags]),
    exclude_tags: dedupeStrings([...(params.exclude_tags || []), ...tokenized.excludeTags]),
    tag_logic: params.tag_logic === 'or' ? 'or' : 'and',
    keywords: buildKeywordString(tokenized.text, includeAuthorNames),
    include_authors: toApiIntIdList(includeAuthorIds),
    exclude_authors: toApiIntIdList(excludeAuthorIds),
    // 后端路由目前实际不消费 request.author_name，
    // 所以作者名搜索改走 keywords 中的 author: 语法。
    author_name: params.author_name || null,
    // 作者反选如果没有作者 ID 映射接口，先不要错误地降级成 exclude_keywords，
    // 否则会变成“排除正文包含作者名的帖子”，语义和性能都不对。
    exclude_keywords: null,
    search_by_collection: params.search_by_collection || false,
    created_after: params.created_after || null,
    created_before: params.created_before || null,
    active_after: params.active_after || null,
    active_before: params.active_before || null,
    sort_method: mapSortMethod(params.sort_method),
    sort_order: 'desc',
    limit: params.limit || 24,
    offset: params.offset || 0,
    exclude_thread_ids: [],
    reaction_count_range: DEFAULT_NUMERIC_RANGE,
    reply_count_range: DEFAULT_NUMERIC_RANGE,
    custom_base_sort: 'comprehensive',
  };

  return requestBody;
}

export const searchApi = {
  search: async (params: SearchUIRequest = {}): Promise<SearchResponse> => {
    const requestBody = buildSearchRequest(params);
    const response = await apiClient.post<SearchResponse>('/search/', requestBody);
    return response.data;
  },

  getThread: async (threadId: string): Promise<Thread> => {
    const response = await apiClient.get<Thread>(`/threads/${threadId}`);
    return response.data;
  },

  // 兼容没有 /meta/channels 的后端：通过逐频道 search 聚合频道标签目录
  getChannelTagCatalog: async (): Promise<ChannelTagCatalogItem[]> => {
    const channels = CHANNEL_CATEGORIES.flatMap((category) => category.channels);
    const uniqueChannels = Array.from(new Map(channels.map((channel) => [channel.id, channel])).values());
    const catalog: ChannelTagCatalogItem[] = [];
    let failedCount = 0;

    for (let i = 0; i < uniqueChannels.length; i += GLOBAL_TAG_DISCOVERY_BATCH_SIZE) {
      const batch = uniqueChannels.slice(i, i + GLOBAL_TAG_DISCOVERY_BATCH_SIZE);
      const responses = await Promise.all(
        batch.map(async (channel) => {
          try {
            const result = await searchApi.search({
              channel_ids: [channel.id],
              limit: 1,
            });
            return {
              channel_id: channel.id,
              channel_name: channel.name,
              available_tags: Array.from(
                new Set((result.available_tags || []).map((tag) => tag.trim()).filter(Boolean)),
              ),
              virtual_tags: Array.from(
                new Set((result.virtual_tags || []).map((tag) => tag.trim()).filter(Boolean)),
              ),
            } satisfies ChannelTagCatalogItem;
          } catch {
            failedCount += 1;
            return null;
          }
        }),
      );

      for (const item of responses) {
        if (!item) continue;
        catalog.push(item);
      }
    }

    if (failedCount > 0) {
      console.warn(
        `[searchApi.getChannelTagCatalog] ${failedCount}/${uniqueChannels.length} channel catalog requests failed.`,
      );
    }

    return catalog;
  },

  // 兼容没有 /meta/channels 的后端：通过逐频道 search 聚合全局标签
  getGlobalTags: async (): Promise<string[]> => {
    const tagSet = new Set<string>();
    const catalog = await searchApi.getChannelTagCatalog();
    for (const item of catalog) {
      for (const tag of item.virtual_tags) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
      for (const tag of item.available_tags) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
    }

    return Array.from(tagSet);
  },
};
