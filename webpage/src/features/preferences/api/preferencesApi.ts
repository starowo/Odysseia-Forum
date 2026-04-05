import { apiClient } from '@/shared/api/client';
import type { components } from '@shared-types/openapi';

type RawUserPreferencesResponse = components['schemas']['UserPreferencesResponse'];
type RawUserPreferencesUpdateRequest = components['schemas']['UserPreferencesUpdateRequest'];

export type UserPreferencesResponse = Omit<RawUserPreferencesResponse, 'preferred_channels'> & {
  preferred_channels?: string[] | null;
};

export type UserPreferencesUpdateRequest = Omit<RawUserPreferencesUpdateRequest, 'preferred_channels'> & {
  preferred_channels?: string[] | null;
};

export interface PreferencesApiOptions {
  guildId?: string | number;
}

function toGuildQuery(guildId?: string | number) {
  if (guildId === undefined || guildId === null || guildId === '') {
    return undefined;
  }
  return { guild_id: guildId };
}

function parsePreferencesResponseText(text: string): UserPreferencesResponse {
  const patched = text.replace(
    /(\"preferred_channels\"\s*:\s*)\[(.*?)\]/,
    (_match, prefix: string, inner: string) => {
      const normalized = inner
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
        .map((item) => item.replace(/^"|"$/g, ''))
        .map((item) => `"${item}"`)
        .join(',');
      return `${prefix}[${normalized}]`;
    },
  );

  return JSON.parse(patched) as UserPreferencesResponse;
}

function normalizePreferencesPayload(payload: UserPreferencesUpdateRequest): RawUserPreferencesUpdateRequest {
  return {
    ...payload,
    preferred_channels: (payload.preferred_channels || []) as unknown as number[] | null,
  };
}

export const preferencesApi = {
  getByUserId: async (
    userId: string | number,
    options: PreferencesApiOptions = {},
  ): Promise<UserPreferencesResponse> => {
    const response = await apiClient.get<string>(
      `/preferences/users/${encodeURIComponent(String(userId))}`,
      {
        params: toGuildQuery(options.guildId),
        responseType: 'text',
        transformResponse: [(data) => data],
      },
    );
    return parsePreferencesResponseText(response.data);
  },

  updateByUserId: async (
    userId: string | number,
    payload: UserPreferencesUpdateRequest,
    options: PreferencesApiOptions = {},
  ): Promise<UserPreferencesResponse> => {
    const response = await apiClient.put<string>(
      `/preferences/users/${encodeURIComponent(String(userId))}`,
      normalizePreferencesPayload(payload),
      {
        params: toGuildQuery(options.guildId),
        responseType: 'text',
        transformResponse: [(data) => data],
      },
    );
    return parsePreferencesResponseText(response.data);
  },
};
