import { apiClient } from '@/shared/api/client';
import type { components } from '@shared-types/openapi';

export type UserPreferencesResponse = components['schemas']['UserPreferencesResponse'];
export type UserPreferencesUpdateRequest = components['schemas']['UserPreferencesUpdateRequest'];

export interface PreferencesApiOptions {
  guildId?: string | number;
}

function toGuildQuery(guildId?: string | number) {
  if (guildId === undefined || guildId === null || guildId === '') {
    return undefined;
  }
  return { guild_id: guildId };
}

export const preferencesApi = {
  getByUserId: async (
    userId: string | number,
    options: PreferencesApiOptions = {},
  ): Promise<UserPreferencesResponse> => {
    const response = await apiClient.get<UserPreferencesResponse>(
      `/preferences/users/${encodeURIComponent(String(userId))}`,
      {
        params: toGuildQuery(options.guildId),
      },
    );
    return response.data;
  },

  updateByUserId: async (
    userId: string | number,
    payload: UserPreferencesUpdateRequest,
    options: PreferencesApiOptions = {},
  ): Promise<UserPreferencesResponse> => {
    const response = await apiClient.put<UserPreferencesResponse>(
      `/preferences/users/${encodeURIComponent(String(userId))}`,
      payload,
      {
        params: toGuildQuery(options.guildId),
      },
    );
    return response.data;
  },
};
