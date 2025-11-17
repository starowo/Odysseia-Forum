import { apiClient } from '@/lib/api/client';

export interface User {
  id: string;
  username: string;
  global_name?: string;
  avatar?: string;
}

export interface AuthResponse {
  loggedIn: boolean;
  user?: User;
  // 当前用户关注列表的未读更新数量（来自 /auth/checkauth）
  unread_count?: number;
}

export const authApi = {
  checkAuth: async (): Promise<AuthResponse> => {
    try {
      const response = await apiClient.get<AuthResponse>('/auth/checkauth');
      return response.data;
    } catch (error) {
      // 如果检查失败，返回未认证状态而不是抛出错误
      return { loggedIn: false };
    }
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
    localStorage.removeItem('auth_token');
  },
};
