import type { UserPreferencesResponse } from '@/features/preferences/api/preferencesApi';
import { toPreferencesFormValue } from '@/features/preferences/lib/preferencesMapper';
import type { UISortMethod } from '@/features/search/api/searchApi';

export type DiscoveryPreferenceMode = 'browse-empty' | 'suggestion' | 'plaza';

export interface DiscoveryPreferenceContext {
  preferredChannelIds: string[];
  includeTags: string[];
  excludeTags: string[];
  sortMethod?: UISortMethod;
  resultsPerPage?: number;
  signature: string;
}

export interface DiscoveryPreferenceRequestPatch {
  channel_ids?: string[];
  include_tags?: string[];
  exclude_tags?: string[];
  sort_method?: UISortMethod;
  limit?: number;
}

interface ResolveDiscoveryPreferenceOptions {
  preferences?: UserPreferencesResponse | null;
  mode: DiscoveryPreferenceMode;
  query?: string;
  selectedChannel?: string | null;
  hasExplicitFilters?: boolean;
}

function normalizeStringList(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

export interface PreferenceTagState {
  includeTags: string[];
  excludeTags: string[];
}

export function getPreferenceTagState(
  preferences?: UserPreferencesResponse | null,
): PreferenceTagState {
  const context = getDiscoveryPreferenceContext(preferences);

  return {
    includeTags: context?.includeTags || [],
    excludeTags: context?.excludeTags || [],
  };
}

export function mergePreferenceTagsWithManual({
  manualIncludeTags,
  manualExcludeTags,
  preferenceIncludeTags,
  preferenceExcludeTags,
  syncPreferenceTags,
}: {
  manualIncludeTags: string[];
  manualExcludeTags: string[];
  preferenceIncludeTags: string[];
  preferenceExcludeTags: string[];
  syncPreferenceTags: boolean;
}): PreferenceTagState {
  const manualInclude = new Set(normalizeStringList(manualIncludeTags));
  const manualExclude = new Set(normalizeStringList(manualExcludeTags));

  if (!syncPreferenceTags) {
    return {
      includeTags: Array.from(manualInclude),
      excludeTags: Array.from(manualExclude),
    };
  }

  const effectiveInclude = new Set(
    normalizeStringList(preferenceIncludeTags).filter((tag) => !manualExclude.has(tag)),
  );
  const effectiveExclude = new Set(
    normalizeStringList(preferenceExcludeTags).filter((tag) => !manualInclude.has(tag)),
  );

  for (const tag of manualInclude) {
    effectiveInclude.add(tag);
    effectiveExclude.delete(tag);
  }

  for (const tag of manualExclude) {
    effectiveExclude.add(tag);
    effectiveInclude.delete(tag);
  }

  return {
    includeTags: Array.from(effectiveInclude),
    excludeTags: Array.from(effectiveExclude),
  };
}

export function getDiscoveryPreferenceContext(
  preferences?: UserPreferencesResponse | null,
): DiscoveryPreferenceContext | null {
  if (!preferences) return null;

  const mapped = toPreferencesFormValue(preferences);
  const preferredChannelIds = normalizeStringList(mapped.preferredChannelIds);
  const includeTags = normalizeStringList(
    mapped.includeTagsText.split(',').map((item) => item.trim()),
  );
  const excludeTags = normalizeStringList(
    mapped.excludeTagsText.split(',').map((item) => item.trim()),
  );
  const sortMethod = mapped.sortMethod;
  const resultsPerPage = Number.isFinite(mapped.resultsPerPage) ? mapped.resultsPerPage : undefined;

  const hasUsefulContent =
    preferredChannelIds.length > 0 ||
    includeTags.length > 0 ||
    excludeTags.length > 0 ||
    false;

  if (!hasUsefulContent) return null;

  return {
    preferredChannelIds,
    includeTags,
    excludeTags,
    sortMethod,
    resultsPerPage,
    signature: JSON.stringify({
      preferredChannelIds,
      includeTags,
      excludeTags,
      sortMethod,
      resultsPerPage,
    }),
  };
}

export function resolveDiscoveryPreferencePatch({
  preferences,
  mode,
  query,
  selectedChannel,
  hasExplicitFilters = false,
}: ResolveDiscoveryPreferenceOptions): DiscoveryPreferenceRequestPatch | null {
  const context = getDiscoveryPreferenceContext(preferences);
  if (!context) return null;

  const normalizedQuery = (query || '').trim();

  if (mode === 'browse-empty') {
    if (normalizedQuery || selectedChannel || hasExplicitFilters) {
      return null;
    }

    return {
      channel_ids: context.preferredChannelIds.length > 0 ? context.preferredChannelIds : undefined,
      sort_method: context.sortMethod,
      limit: context.resultsPerPage,
    };
  }

  if (mode === 'plaza') {
    return {
      channel_ids: context.preferredChannelIds.length > 0 ? context.preferredChannelIds : undefined,
      include_tags: context.includeTags.length > 0 ? context.includeTags : undefined,
      exclude_tags: context.excludeTags.length > 0 ? context.excludeTags : undefined,
    };
  }

  return {
    channel_ids: !selectedChannel && context.preferredChannelIds.length > 0
      ? context.preferredChannelIds
      : undefined,
  };
}
