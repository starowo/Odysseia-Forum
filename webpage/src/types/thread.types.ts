// 帖子相关类型定义

export interface Author {
  id: string;
  name: string;
  global_name?: string;
  display_name?: string;
  avatar?: string;  // 保留用于向后兼容
  avatar_url?: string;  // 后端实际返回的字段
}

export interface Thread {
  // 后端 ThreadDetail 必备字段
  thread_id: string;
  channel_id: string;
  title: string;
  author?: Author;
  created_at: string;
  last_active_at?: string | null;
  reaction_count: number;
  reply_count: number;
  display_count?: number;
  first_message_excerpt?: string | null;
  thumbnail_url?: string | null;
  thumbnail_urls?: string[] | null;
  tags: string[];

  // 部分接口中的扩展字段（例如关注列表等）
  id?: string;
  guild_id?: string;
  author_id?: string;
  is_following?: boolean;
  has_update?: boolean;
}

export interface SearchParams {
  query?: string;
  channel_ids?: string[] | null;
  include_tags?: string[];
  exclude_tags?: string[];
  tag_logic?: 'and' | 'or';
  author_name?: string;
  created_after?: string | null;
  created_before?: string | null;
  sort_method?: 'relevance' | 'last_active_desc' | 'created_desc' | 'reply_desc' | 'reaction_desc';
  limit?: number;
  offset?: number;
}

export interface SearchResponse {
  results: Thread[];
  total: number;
  limit: number;
  offset: number;
  available_tags: string[];
  banner_carousel?: BannerItem[];
  unread_count?: number;
}

export interface BannerItem {
  thread_id: string;
  channel_id: string;
  title: string;
  description?: string;
  cover_image_url: string;
}

export interface TagDetail {
  id: string;
  name: string;
}

export interface Channel {
  id: string;
  name: string;
  tags?: TagDetail[];
}

export interface ChannelCategory {
  name: string;
  channels: Channel[];
}
