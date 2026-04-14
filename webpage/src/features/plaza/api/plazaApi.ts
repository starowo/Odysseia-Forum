import type { SearchResponse, Thread, Author } from '@/entities/thread/types';
import type { Booklist } from '@/entities/booklist/types';
import { searchApi } from '@/features/search/api/searchApi';
import { bannerApi } from '@/features/banner/api/bannerApi';
import { booklistsApi } from '@/features/booklists/api/booklistsApi';

export interface PlazaBannerItem {
  thread_id: string;
  title: string;
  cover_image_url: string;
  channel_id?: string;
  author?: Author;
}

export type PlazaRailKey =
  | 'latest'
  | 'reaction_surge'
  | 'discussion_surge'
  | 'editors_pick';

export interface PlazaRailConfig {
  key: PlazaRailKey;
  title: string;
  subtitle: string;
}

export interface PlazaPreferenceFilter {
  channel_ids?: string[];
  include_tags?: string[];
  exclude_tags?: string[];
}

export const PLAZA_RAILS: PlazaRailConfig[] = [
  {
    key: 'latest',
    title: '最近上新',
    subtitle: '按发布时间倒序，追踪最新内容',
  },
  {
    key: 'reaction_surge',
    title: '点赞数飙升',
    subtitle: '近 7 天互动强势增长的帖子',
  },
  {
    key: 'discussion_surge',
    title: '讨论升温',
    subtitle: '近 7 天回复活跃的讨论串',
  },
  {
    key: 'editors_pick',
    title: '今日精选',
    subtitle: '综合排序下的高质量探索位',
  },
];

function dedupeThreads(threads: Thread[]): Thread[] {
  const map = new Map<string, Thread>();
  for (const thread of threads) {
    if (!thread?.thread_id) continue;
    if (!map.has(thread.thread_id)) map.set(thread.thread_id, thread);
  }
  return Array.from(map.values());
}

export const plazaApi = {
  getBanners: async (): Promise<PlazaBannerItem[]> => {
    const result = await bannerApi.getActiveBanners();
    const items = Array.isArray(result?.banners) ? result.banners : [];
    return items.map((item: any) => ({
      thread_id: String(item.thread_id ?? ''),
      title: String(item.title ?? ''),
      cover_image_url: String(item.cover_image_url ?? ''),
      channel_id: item.channel_id ? String(item.channel_id) : undefined,
      author: item.author,
    }));
  },

  getRail: async (key: PlazaRailKey, preferenceFilter?: PlazaPreferenceFilter): Promise<Thread[]> => {
    let response: SearchResponse;
    const baseFilter = {
      channel_ids: preferenceFilter?.channel_ids,
      include_tags: preferenceFilter?.include_tags,
      exclude_tags: preferenceFilter?.exclude_tags,
    };

    if (key === 'latest') {
      response = await searchApi.search({
        ...baseFilter,
        sort_method: 'created_desc',
        limit: 12,
      });
    } else if (key === 'reaction_surge') {
      response = await searchApi.search({
        ...baseFilter,
        sort_method: 'reaction_desc',
        created_after: '-7d',
        limit: 12,
      });
    } else if (key === 'discussion_surge') {
      response = await searchApi.search({
        ...baseFilter,
        sort_method: 'reply_desc',
        active_after: '-7d',
        limit: 12,
      });
    } else {
      response = await searchApi.search({
        ...baseFilter,
        sort_method: 'relevance',
        limit: 12,
      });
    }

    return dedupeThreads((response.results || []) as Thread[]).slice(0, 8);
  },

  getFeaturedBooklists: async (): Promise<Booklist[]> => {
    const response = await booklistsApi.listPublic({
      sortMethod: 3,
      sortOrder: 'desc',
      pageIndex: 0,
      pageSize: 6,
    });
    return response.results || [];
  },
};
