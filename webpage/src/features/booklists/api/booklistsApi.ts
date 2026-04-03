import { apiClient } from '@/shared/api/client';
import type {
  Booklist,
  BooklistCreateResponse,
  BooklistFormInput,
  BooklistItem,
  BooklistItemAddInput,
  BooklistItemUpdateInput,
  BooklistUpdateResponse,
  PaginatedResponse,
} from '@/entities/booklist/types';

interface BooklistListRequest {
  pageIndex?: number;
  pageSize?: number;
  keywords?: string;
  sortMethod?: number;
  sortOrder?: 'asc' | 'desc';
  ownerId?: number;
  includedThreadId?: number;
}

interface MyBooklistListRequest {
  pageIndex?: number;
  pageSize?: number;
  keywords?: string;
  sortMethod?: number;
  sortOrder?: 'asc' | 'desc';
  isPublic?: boolean;
  collectByCurrentUser?: boolean;
  createByCurrentUser?: boolean;
}

function toPageParams(pageIndex = 0, pageSize = 12) {
  return {
    offset: pageIndex,
    limit: pageSize,
  };
}

export const booklistsApi = {
  listPublic: async (params: BooklistListRequest = {}): Promise<PaginatedResponse<Booklist>> => {
    const response = await apiClient.get<PaginatedResponse<Booklist>>('/booklist/list/page', {
      params: {
        ...toPageParams(params.pageIndex, params.pageSize),
        keywords: params.keywords || undefined,
        owner_id: params.ownerId,
        included_thread_id: params.includedThreadId,
        sort_method: params.sortMethod ?? 4,
        sort_order: params.sortOrder ?? 'desc',
      },
    });
    return response.data;
  },

  listMine: async (params: MyBooklistListRequest = {}): Promise<PaginatedResponse<Booklist>> => {
    const response = await apiClient.get<PaginatedResponse<Booklist>>('/booklist/my/list/page', {
      params: {
        ...toPageParams(params.pageIndex, params.pageSize),
        keywords: params.keywords || undefined,
        is_public: params.isPublic,
        collect_by_current_user: params.collectByCurrentUser,
        create_by_current_user: params.createByCurrentUser,
        sort_method: params.sortMethod ?? (params.collectByCurrentUser ? 6 : 4),
        sort_order: params.sortOrder ?? 'desc',
      },
    });
    return response.data;
  },

  getDetail: async (booklistId: number): Promise<Booklist> => {
    const response = await apiClient.get<Booklist>(`/booklist/detail/${booklistId}`);
    return response.data;
  },

  create: async (payload: BooklistFormInput): Promise<BooklistCreateResponse> => {
    const response = await apiClient.post<BooklistCreateResponse>('/booklist/save', null, {
      params: {
        title: payload.title,
        description: payload.description || undefined,
        cover_image_url: payload.cover_image_url || undefined,
        is_public: payload.is_public,
        display_type: payload.display_type,
      },
    });
    return response.data;
  },

  update: async (booklistId: number, payload: Partial<BooklistFormInput>): Promise<BooklistUpdateResponse> => {
    const response = await apiClient.put<BooklistUpdateResponse>(`/booklist/update/${booklistId}`, null, {
      params: {
        title: payload.title,
        description: payload.description,
        cover_image_url: payload.cover_image_url,
        is_public: payload.is_public,
        display_type: payload.display_type,
      },
    });
    return response.data;
  },

  remove: async (booklistId: number): Promise<void> => {
    await apiClient.delete(`/booklist/delete/${booklistId}`);
  },

  listItems: async (
    booklistId: number,
    pageIndex = 0,
    pageSize = 24,
  ): Promise<PaginatedResponse<BooklistItem>> => {
    const response = await apiClient.get<PaginatedResponse<BooklistItem>>(
      `/booklist/item/list/page/${booklistId}`,
      {
        params: toPageParams(pageIndex, pageSize),
      },
    );
    return response.data;
  },

  addItems: async (booklistId: number, items: BooklistItemAddInput[]): Promise<void> => {
    await apiClient.post(`/booklist/item/add/${booklistId}`, { items });
  },

  removeItems: async (booklistId: number, threadIds: number[]): Promise<void> => {
    await apiClient.delete(`/booklist/item/delete/${booklistId}`, {
      data: { thread_ids: threadIds },
    });
  },

  updateItem: async (booklistId: number, threadId: number, payload: BooklistItemUpdateInput): Promise<BooklistItem> => {
    const response = await apiClient.patch<BooklistItem>(`/booklist/item/update/${booklistId}/${threadId}`, payload);
    return response.data;
  },

  collect: async (booklistIds: number[]): Promise<void> => {
    await apiClient.post('/collection/batch/add', booklistIds, {
      params: {
        target_type: 2,
      },
    });
  },

  uncollect: async (booklistIds: number[]): Promise<void> => {
    await apiClient.post('/collection/batch/remove', booklistIds, {
      params: {
        target_type: 2,
      },
    });
  },
};
