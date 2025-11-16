import { http, HttpResponse } from 'msw';

// 从旧的 mockAuth.ts 导入模拟用户数据
const MOCK_USER = {
  id: '123456789',
  username: 'demo_user',
  global_name: 'Demo User',
  avatar: '1234567890abcdef',
};

export const handlers = [
  // 拦截登录请求
  http.post('/api/v1/auth/login', () => {
    // 在 msw 里，我们不直接操作 localStorage，
    // 而是模拟后端返回一个包含 token 的成功响应。
    // 前端拿到 token 后自然会去存。
    return HttpResponse.json({
      token: `mock_jwt_token_${Date.now()}`,
    });
  }),

  // 拦截检查用户状态的请求
  http.get('/api/v1/auth/checkauth', () => {
    // 这里模拟用户已登录的情况
    return HttpResponse.json({
      loggedIn: true,
      user: MOCK_USER,
    });

    // 如果想模拟用户未登录，可以返回一个 401 错误
    // return new HttpResponse(null, { status: 401 });
  }),

  // 拦截登出请求
  http.post('/api/v1/auth/logout', () => {
    // 模拟后端成功处理了登出
    return new HttpResponse(null, { status: 204 });
  }),
];