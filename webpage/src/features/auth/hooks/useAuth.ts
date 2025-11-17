import { useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi } from '../api/authApi';

export function useAuth() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['auth'],
    queryFn: authApi.checkAuth,
    staleTime: 5 * 60 * 1000, // 5分钟内不重新请求
    gcTime: 10 * 60 * 1000, // 缓存10分钟
    retry: false,
    refetchOnWindowFocus: false, // 不在窗口聚焦时重新获取
    refetchOnMount: false, // 不在组件挂载时重新获取（使用缓存）
    refetchOnReconnect: false, // 不在重新连接时重新获取
  });

  return {
    user: data?.user,
    isAuthenticated: data?.loggedIn ?? false,
    // 从后端 /auth/checkauth 获取的关注未读数量（MSW 也会模拟该字段）
    unreadCount: data?.unread_count ?? 0,
    isLoading,
    error,
    refetch,
  };
}

// 用于登录后刷新认证状态的 hook
export function useRefreshAuth() {
  const queryClient = useQueryClient();
  
  return () => {
    queryClient.invalidateQueries({ queryKey: ['auth'] });
  };
}
