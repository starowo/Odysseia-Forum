// 开发模式的模拟认证服务
// 仅用于 UI 开发，不连接真实后端

export const MOCK_USER = {
  id: '123456789',
  username: 'demo_user',
  global_name: 'Demo User',
  avatar: '1234567890abcdef',
};

export const mockAuthApi = {
  // 模拟登录
  login: () => {
    const mockToken = 'mock_token_' + Date.now();
    localStorage.setItem('auth_token', mockToken);
    localStorage.setItem('mock_user', JSON.stringify(MOCK_USER));
    return Promise.resolve({ success: true });
  },

  // 模拟检查认证状态
  checkAuth: () => {
    const token = localStorage.getItem('auth_token');
    const user = localStorage.getItem('mock_user');
    
    if (token && user) {
      return Promise.resolve({
        loggedIn: true,
        user: JSON.parse(user),
      });
    }
    
    return Promise.resolve({
      loggedIn: false,
    });
  },

  // 模拟登出
  logout: () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('mock_user');
    return Promise.resolve();
  },
};

// 检查是否启用Mock模式（仅用于UI开发，不连接真实后端）
export const isDevelopmentMode = () => {
  return import.meta.env.VITE_USE_MOCK_AUTH === 'true';
};
