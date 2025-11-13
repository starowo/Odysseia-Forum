import { apiClient } from '@/lib/api/client';
import { mockAuthApi, isDevelopmentMode } from '@/lib/mockAuth';

export interface User {
  id: string;
  username: string;
  global_name?: string;
  avatar?: string;
}

export interface AuthResponse {
  loggedIn: boolean;
  user?: User;
}

export const authApi = {
  checkAuth: async (): Promise<AuthResponse> => {
    // 开发模式使用 mock 数据
    if (isDevelopmentMode()) {
      return mockAuthApi.checkAuth();
    }
    
    try {
      const response = await apiClient.get<AuthResponse>('/auth/checkauth');
      return response.data;
    } catch (error) {
      // 如果检查失败，返回未认证状态而不是抛出错误
      return { loggedIn: false };
    }
  },

  logout: async (): Promise<void> => {
    // 开发模式使用 mock 数据
    if (isDevelopmentMode()) {
      return mockAuthApi.logout();
    }
    
    await apiClient.post('/auth/logout');
    localStorage.removeItem('auth_token');
  },
};
