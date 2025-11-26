import { apiClient } from '@/lib/api/client';
import type { SearchParams, SearchResponse, Channel } from '@/types/thread.types';

// 构建搜索请求参数
function buildSearchRequest(params: SearchParams) {
  const sortMap: Record<string, { method: string; order: string }> = {
    relevance: { method: 'comprehensive', order: 'desc' },
    last_active_desc: { method: 'last_active', order: 'desc' },
    created_desc: { method: 'created_at', order: 'desc' },
    reply_desc: { method: 'reply_count', order: 'desc' },
    reaction_desc: { method: 'reaction_count', order: 'desc' },
  };

  const sortConfig = sortMap[params.sort_method || 'last_active_desc'] || sortMap.relevance;

  return {
    channel_ids: params.channel_ids,
    include_tags: params.include_tags || [],
    exclude_tags: params.exclude_tags || [],
    tag_logic: params.tag_logic || 'and',
    keywords: params.query || null,
    author_name: params.author_name || undefined,
    created_after: params.created_after,
    created_before: params.created_before,
    sort_method: sortConfig.method,
    sort_order: sortConfig.order,
    limit: params.limit || 24,
    offset: params.offset || 0,
  };
}

export const searchApi = {
  // 搜索帖子
  search: async (params: SearchParams): Promise<SearchResponse> => {
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
  getThread: async (threadId: string): Promise<import('@/types/thread.types').Thread> => {
    const response = await apiClient.get<import('@/types/thread.types').Thread>(`/threads/${threadId}`);
    return response.data;
  },
};
