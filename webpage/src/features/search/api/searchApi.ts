import { apiClient } from '@/shared/api/client';
import type { SearchResponse, Channel, Thread } from '@/entities/thread/types';
import type { components } from '@shared-types/openapi';

// 构建搜索请求参数
function buildSearchRequest(params: any): components["schemas"]["SearchRequest"] {
  const sortMap: Record<string, { method: string; order: string }> = {
    relevance: { method: 'comprehensive', order: 'desc' },
    last_active_desc: { method: 'last_active', order: 'desc' },
    created_desc: { method: 'created_at', order: 'desc' },
    reply_desc: { method: 'reply_count', order: 'desc' },
    reaction_desc: { method: 'reaction_count', order: 'desc' },
  };

  const sortConfig = sortMap[params.sort_method || 'last_active_desc'] || sortMap.relevance;

  return {
    keywords: params.query || null,
    channel_ids: params.channel_ids || null,
    include_tags: params.include_tags || [],
    exclude_tags: params.exclude_tags || [],
    tag_logic: params.tag_logic === 'or' ? 'or' : 'and',
    author_name: params.author_name || null,
    created_after: params.created_after || null,
    created_before: params.created_before || null,
    active_after: null,
    active_before: null,
    sort_method: sortConfig.method,
    custom_base_sort: 'comprehensive',
    sort_order: sortConfig.order,
    limit: params.limit || 24,
    offset: params.offset || 0,
  } as any;
}

export const searchApi = {
  // 搜索帖子
  search: async (params: any): Promise<SearchResponse> => {
    const requestBody = buildSearchRequest(params);
    const response = await apiClient.post<SearchResponse>('/search/', requestBody);
    return response.data;
  },

  // 获取所有频道及其可用标签
  getChannels: async (): Promise<Channel[]> => {
    const response = await apiClient.get<Channel[]>('/meta/channels');
    return response.data;
  },

  // 获取单个帖子详情
  getThread: async (threadId: string): Promise<Thread> => {
    const response = await apiClient.get<Thread>(`/threads/${threadId}`);
    return response.data;
  },
};
