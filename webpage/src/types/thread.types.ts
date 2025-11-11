// 帖子相关类型定义

export interface Author {
  id: string;
  name: string;
  global_name?: string;
  display_name?: string;
  avatar?: string;
}

export interface Thread {
  id: string;
  thread_id: string;
  channel_id: string;
  guild_id: string;
  title: string;
  author: Author;
  author_id: string;
  tags: string[];
  created_at: string;
  last_active_at: string;
  reply_count: number;
  reaction_count: number;
  thumbnail_url?: string;
  first_message_excerpt?: string;
  is_following?: boolean;
  has_update?: boolean;
}

export interface SearchParams {
  query?: string;
  channel_ids?: string[] | null;
  include_tags?: string[];
  exclude_tags?: string[];
  tag_logic?: 'and' | 'or';
  created_after?: string | null;
  created_before?: string | null;
  sort_method?: 'comprehensive' | 'last_active' | 'created_at' | 'reply_count' | 'reaction_count';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface SearchResponse {
  results: Thread[];
  total: number;
  available_tags: string[];
  banner_carousel?: BannerItem[];
}

export interface BannerItem {
  thread_id: string;
  channel_id: string;
  title: string;
  cover_image_url: string;
}

export interface Channel {
  id: string;
  name: string;
}

export interface ChannelCategory {
  name: string;
  channels: Channel[];
}
