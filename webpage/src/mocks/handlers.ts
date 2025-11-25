import { http, HttpResponse, type RequestHandler } from 'msw';
import {
  MOCK_META_CHANNELS,
  MOCK_THREADS,
  FOLLOWED_THREAD_IDS,
  UPDATED_THREAD_IDS,
  createMockThread,
  followThread,
  unfollowThread,
  markThreadUpdated,
  resetMockData,
  getMockState,
} from './data';

const MOCK_USER = {
  id: '123456789',
  username: 'demo_user',
  global_name: 'Demo User',
  avatar: null,
};

export const handlers: RequestHandler[] = [
  // Intercept login request - redirect with hash token
  http.get('http://localhost:10810/v1/auth/login', () => {
    const token = `mock_jwt_token_${Date.now()}`;
    // Simulate redirect to callback with hash (matching Worker behavior)
    return HttpResponse.redirect(`http://localhost:5173/auth/callback#token=${token}`, 302);
  }),

  // Intercept auth check request
  http.get('http://localhost:10810/v1/auth/checkauth', () => {
    return HttpResponse.json({
      loggedIn: true,
      user: MOCK_USER,
      // Simulate unread count from followed threads
      unread_count: UPDATED_THREAD_IDS.length,
    });
  }),

  // Intercept logout request - should be GET
  http.get('http://localhost:10810/v1/auth/logout', () => {
    return new HttpResponse(null, { status: 200 });
  }),

  // 拦截获取频道列表的请求（与 /v1/meta/channels: List[Channel] 对齐）
  http.get('http://localhost:10810/v1/meta/channels', () => {
    return HttpResponse.json(MOCK_META_CHANNELS);
  }),


  // 拦截获取关注列表的请求（与 /v1/follows/ 对齐）
  http.get('http://localhost:10810/v1/follows/', () => {
    const followedSet = new Set(FOLLOWED_THREAD_IDS);
    const updatedSet = new Set(UPDATED_THREAD_IDS);

    const followedThreads = MOCK_THREADS.filter((thread) => followedSet.has(thread.thread_id)).map(
      (thread) => ({
        ...thread,
        // 关注列表结果里补充 id 字段，方便用作 React key
        id: thread.thread_id,
        is_following: true,
        has_update: updatedSet.has(thread.thread_id),
      }),
    );

    return HttpResponse.json({
      total: followedThreads.length,
      threads: followedThreads,
      limit: 10000,
      offset: 0,
    });
  }),

  // 拦截获取关注未读数量的请求（/v1/follows/unread-count）
  http.get('http://localhost:10810/v1/follows/unread-count', () => {
    const followedSet = new Set(FOLLOWED_THREAD_IDS);
    const updatedSet = new Set(UPDATED_THREAD_IDS);

    const followedThreads = MOCK_THREADS.filter((thread) => followedSet.has(thread.thread_id)).map(
      (thread) => ({
        ...thread,
        has_update: updatedSet.has(thread.thread_id),
      }),
    );

    const unreadCount = followedThreads.filter((t) => t.has_update).length;

    return HttpResponse.json({
      unread_count: unreadCount,
    });
  }),

  // 拦截搜索请求（本地 Mock）。生产环境不会启用 MSW。
  // 注意：路径与 apiClient.post('/search/') 拼出的完整 URL 精确对齐
  http.post('http://localhost:10810/v1/search/', async ({ request }) => {
    const reqBody = (await request.json()) as {
      // 实际后端使用 "keywords"，我们同时兼容 "query"
      query?: string | null;
      keywords?: string | null;
      channel_ids?: string[] | null;
      include_tags?: string[];
      exclude_tags?: string[];
      tag_logic?: 'and' | 'or';
      created_after?: string | null;
      created_before?: string | null;
      offset?: number;
      limit?: number;
    };

    const {
      query,
      keywords,
      channel_ids,
      include_tags = [],
      exclude_tags = [],
      tag_logic = 'and',
      created_after,
      created_before,
      offset = 0,
      limit = 24,
    } = reqBody;

    let filtered = [...MOCK_THREADS];

    // 关键词匹配：标题 + 摘要 + 作者（支持 author:xxx 语法）
    const rawSearchText = (keywords ?? query ?? '').trim();
    let searchText = rawSearchText;
    let authorFilter: string | null = null;

    // 解析 author: 前缀（例如 author:用户1 或 author:用户1 LLM）
    if (rawSearchText) {
      const lower = rawSearchText.toLowerCase();
      const prefix = 'author:';
      const idx = lower.indexOf(prefix);
      if (idx !== -1) {
        const after = rawSearchText.slice(idx + prefix.length).trim();
        if (after) {
          authorFilter = after.toLowerCase();
        }
        // 剩余部分作为普通关键词
        searchText = rawSearchText.slice(0, idx).trim();
      }
    }

    // 普通关键词：匹配标题 + 摘要
    if (searchText) {
      const q = searchText.toLowerCase();
      filtered = filtered.filter((thread) => {
        const inTitle = thread.title.toLowerCase().includes(q);
        const inExcerpt = thread.first_message_excerpt?.toLowerCase().includes(q) ?? false;
        return inTitle || inExcerpt;
      });
    }

    // 作者过滤：匹配 display_name / name（mock author 没有 global_name 字段）
    if (authorFilter) {
      filtered = filtered.filter((thread) => {
        const names = [thread.author?.display_name, thread.author?.name].filter(Boolean) as string[];
        return names.some((name) => name.toLowerCase().includes(authorFilter!));
      });
    }

    // 频道过滤
    if (Array.isArray(channel_ids) && channel_ids.length > 0) {
      const channelSet = new Set(channel_ids);
      filtered = filtered.filter((thread) => channelSet.has(thread.channel_id));
    }

    // 标签包含过滤
    if (include_tags.length > 0) {
      filtered = filtered.filter((thread) => {
        const threadTagSet = new Set(thread.tags);
        if (tag_logic === 'and') {
          // 所有 include_tags 都必须在帖子标签里
          return include_tags.every((t) => threadTagSet.has(t));
        }
        // OR：至少有一个匹配
        return include_tags.some((t) => threadTagSet.has(t));
      });
    }

    // 标签排除过滤
    if (exclude_tags.length > 0) {
      const excludeSet = new Set(exclude_tags);
      filtered = filtered.filter((thread) => !thread.tags.some((t) => excludeSet.has(t)));
    }

    // 时间范围过滤
    if (created_after) {
      const after = new Date(created_after).getTime();
      filtered = filtered.filter((thread) => new Date(thread.created_at).getTime() >= after);
    }
    if (created_before) {
      const before = new Date(created_before).getTime();
      filtered = filtered.filter((thread) => new Date(thread.created_at).getTime() <= before);
    }

    const total = filtered.length;

    // 分页
    const start = offset;
    const end = start + limit;
    const paginatedThreads = filtered.slice(start, end);

    // 为搜索结果补充“已关注/有更新”标记（使用当前 FOLLOWED_THREAD_IDS / UPDATED_THREAD_IDS 状态）
    const followedSet = new Set(FOLLOWED_THREAD_IDS);
    const updatedSet = new Set(UPDATED_THREAD_IDS);

    const paginatedThreadsWithFlags = paginatedThreads.map((thread) => ({
      ...thread,
      is_following: followedSet.has(thread.thread_id),
      has_update: updatedSet.has(thread.thread_id),
    }));

    // 根据当前结果生成 available_tags（用来填标签筛选区）
    const availableTagsSet = new Set<string>();
    filtered.forEach((thread) => {
      thread.tags.forEach((t) => availableTagsSet.add(t));
    });
    const available_tags = Array.from(availableTagsSet).sort();

    // 选一些带封面的帖子作为 Banner
    const banner_carousel = filtered
      .filter((t) => !!t.thumbnail_url)
      .slice(0, 5)
      .map((t) => ({
        thread_id: t.thread_id,
        channel_id: t.channel_id,
        title: t.title,
        cover_image_url: t.thumbnail_url!,
      }));

    // 按后端 SearchResponse 结构返回：
    // total, limit, offset, results, available_tags, banner_carousel, unread_count
    return HttpResponse.json({
      total,
      limit,
      offset,
      results: paginatedThreadsWithFlags,
      available_tags,
      banner_carousel,
      // 未读数：等于有更新的关注帖子数量
      unread_count: UPDATED_THREAD_IDS.length,
    });
  }),

  // --- Dev-only mock control endpoints，用于本地快速造数据 ---
  http.get('http://localhost:10810/v1/dev/mock/state', () => {
    return HttpResponse.json(getMockState());
  }),

  http.post('http://localhost:10810/v1/dev/mock/add-thread', async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as {
      title?: string;
      channel_id?: string;
      tags?: string[];
      markdown?: string;
      follow?: boolean;
      has_update?: boolean;
    };

    const newThread = createMockThread(body);
    if (body.follow) {
      followThread(newThread.thread_id);
    }
    if (body.has_update) {
      markThreadUpdated(newThread.thread_id, true);
    }

    return HttpResponse.json(newThread);
  }),

  http.post('http://localhost:10810/v1/dev/mock/follow', async ({ request }) => {
    const { thread_id } = (await request.json()) as { thread_id: string };
    followThread(thread_id);
    return HttpResponse.json({ ok: true });
  }),

  http.post('http://localhost:10810/v1/dev/mock/unfollow', async ({ request }) => {
    const { thread_id } = (await request.json()) as { thread_id: string };
    unfollowThread(thread_id);
    return HttpResponse.json({ ok: true });
  }),

  http.post('http://localhost:10810/v1/dev/mock/mark-update', async ({ request }) => {
    const { thread_id, has_update = true } = (await request.json()) as {
      thread_id: string;
      has_update?: boolean;
    };
    markThreadUpdated(thread_id, has_update);
    return HttpResponse.json({ ok: true });
  }),

  http.post('http://localhost:10810/v1/dev/mock/reset', () => {
    resetMockData();
    return HttpResponse.json({ ok: true });
  }),
];