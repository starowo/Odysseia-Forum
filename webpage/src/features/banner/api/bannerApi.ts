import { apiClient } from '@/lib/api/client';

export interface BannerApplicationRequest {
    thread_id: string;
    cover_image_url: string;
    target_scope: string;
}

export interface BannerApplicationResponse {
    success: boolean;
    message: string;
    application_id?: number;
}

export const bannerApi = {
    apply: async (data: BannerApplicationRequest): Promise<BannerApplicationResponse> => {
        const response = await apiClient.post<BannerApplicationResponse>('/banner/apply', data);
        return response.data;
    },

    getActiveBanners: async (channelId?: string) => {
        const response = await apiClient.get('/banner/active', {
            params: { channel_id: channelId },
        });
        return response.data;
    },
};
