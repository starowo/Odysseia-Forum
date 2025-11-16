import { http, HttpResponse, type RequestHandler } from 'msw';
import { MOCK_CHANNELS, MOCK_TAGS, MOCK_THREADS } from './data';

const MOCK_USER = {
  id: '123456789',
  username: 'demo_user',
  global_name: 'Demo User',
  avatar: null,
};

export const handlers: RequestHandler[] = [
  // 拦截登录请求
  http.post('http://localhost:10810/v1/auth/login', () => {
    return HttpResponse.json({
      token: `mock_jwt_token_${Date.now()}`,
    });
  }),

  // 拦截检查用户状态的请求
  http.get('http://localhost:10810/v1/auth/checkauth', () => {
    return HttpResponse.json({
      loggedIn: true,
      user: MOCK_USER,
    });
  }),

  // 拦截登出请求
  http.post('http://localhost:10810/v1/auth/logout', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // 拦截获取频道列表的请求
  http.get('http://localhost:10810/v1/meta/channels', () => {
    return HttpResponse.json(MOCK_CHANNELS);
  }),

  // 拦截获取标签列表的请求
  http.get('http://localhost:10810/v1/meta/tags', () => {
    return HttpResponse.json(MOCK_TAGS);
  }),

  // 拦截搜索请求
  http.post('http://localhost:10810/v1/search', async ({ request }) => {
    const reqBody = (await request.json()) as {
      query?: string;
      tags?: string[];
      offset?: number;
      limit?: number;
    };
    const { offset = 0, limit = 24 } = reqBody;

    const start = offset;
    const end = start + limit;

    const paginatedThreads = MOCK_THREADS.slice(start, end);

    return HttpResponse.json({
      threads: paginatedThreads,
      total: MOCK_THREADS.length,
    });
  }),
];