import { components } from '@shared-types/openapi';

export type Booklist = components['schemas']['BooklistDetail'];
export type BooklistItem = components['schemas']['BooklistItemDetail'];
export type BooklistCreateResponse = components['schemas']['BooklistCreateResponse'];
export type BooklistUpdateResponse = components['schemas']['BooklistUpdateResponse'];

export interface PaginatedResponse<T> {
  total: number;
  limit: number;
  offset: number;
  results: T[];
}

export interface BooklistListParams {
  pageIndex?: number;
  pageSize?: number;
  keywords?: string;
  sortMethod?: number;
  sortOrder?: 'asc' | 'desc';
  isPublic?: boolean;
}

export interface BooklistFormInput {
  title: string;
  description?: string;
  cover_image_url?: string;
  is_public: boolean;
  display_type: number;
}

export interface BooklistItemAddInput {
  thread_id: number;
  comment?: string;
  display_order?: number;
}

export interface BooklistItemUpdateInput {
  comment?: string;
  display_order?: number;
}
