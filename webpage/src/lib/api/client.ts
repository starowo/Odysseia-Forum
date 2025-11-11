import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:10810/v1';

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  withCredentials: true,
});

// 请求拦截器
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 只在非认证检查的请求中处理401
    // 认证检查接口应该由组件自己处理
    if (error.response?.status === 401 && !error.config.url?.includes('/auth/checkauth')) {
      localStorage.removeItem('auth_token');
      // 不要直接跳转，让ProtectedRoute处理
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
