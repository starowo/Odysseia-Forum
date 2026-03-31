import { components } from '@shared-types/openapi';

// --- 基础领域模型 (从 OpenAPI 自动生成类型映射) ---

/**
 * 帖子作者详细信息
 */
export type Author = components["schemas"]["AuthorDetail-Output"];

/**
 * 帖子核心实体 (扩展了后端 OpenAPI 定义以支持前端状态)
 */
export type Thread = components["schemas"]["ThreadDetail-Output"] & {
  id?: string;           // 兼容旧版代码使用的 id (即 thread_id)
  is_following?: boolean; // 兼容旧版关注状态 (后端目前使用 collected_flag)
  has_update?: boolean;   // 兼容旧版未读更新状态
};

/**
 * 搜索请求参数
 */
export type SearchParams = components["schemas"]["SearchRequest"];

/**
 * 搜索响应结果
 */
export type SearchResponse = components["schemas"]["SearchResponse"];

/**
 * Banner 轮播项
 */
export type BannerItem = components["schemas"]["BannerItem-Output"];

// --- 辅助业务模型 (用于前端 UI 展示或逻辑扩展) ---

/**
 * 标签详情
 */
export interface TagDetail {
  id: string;
  name: string;
}

/**
 * 频道实体
 */
export interface Channel {
  id: string;
  name: string;
  tags?: TagDetail[];
}

/**
 * 频道分类 (用于侧边柜等展示)
 */
export interface ChannelCategory {
  name: string;
  channels: Channel[];
}

// 导出 paths 以便在 API 层使用
export type { paths } from '@shared-types/openapi';
