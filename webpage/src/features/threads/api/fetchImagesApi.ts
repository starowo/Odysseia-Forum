import { apiClient } from '@/lib/api/client';

export interface FetchImageItem {
    thread_id: number;
    channel_id?: number;
}

export interface FetchImageRequest {
    items: FetchImageItem[];
}

export interface FetchImageResponseItem {
    thread_id: string;
    thumbnail_urls: string[];
    updated: boolean;
    error?: string;
}

export interface FetchImageResponse {
    results: FetchImageResponseItem[];
}

export const fetchImagesApi = {
    refresh: async (items: FetchImageItem[]): Promise<FetchImageResponse> => {
        const response = await apiClient.post<FetchImageResponse>('/fetch-images/', { items });
        return response.data;
    },
};
