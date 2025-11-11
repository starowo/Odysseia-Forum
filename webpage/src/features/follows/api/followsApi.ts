import { apiClient } from '@/lib/api/client';
import type { Thread } from '@/types/thread.types';

export interface FollowsResponse {
  results: Thread[];
  total: number;
  unread_count: number;
}

export const followsApi = {
  // 获取关注的帖子列表
  getFollows: async (): Promise<FollowsResponse> => {
    const response = await apiClient.get<FollowsResponse>('/preferences/follows');
    return response.data;
  },

  // 关注帖子
  followThread: async (threadId: string): Promise<void> => {
    await apiClient.post(`/preferences/follows/${threadId}`);
  },

  // 取消关注
  unfollowThread: async (threadId: string): Promise<void> => {
    await apiClient.delete(`/preferences/follows/${threadId}`);
  },
};
