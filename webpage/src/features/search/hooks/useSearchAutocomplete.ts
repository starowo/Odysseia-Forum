import { useMemo } from 'react';

import { useQuery } from '@tanstack/react-query';

import { searchApi } from '@/features/search/api/searchApi';
import type { UserPreferencesResponse } from '@/features/preferences/api/preferencesApi';
import {
  getDiscoveryPreferenceContext,
  mergePreferenceTagsWithManual,
  resolveDiscoveryPreferencePatch,
} from '@/features/preferences/lib/discoveryPreferences';
import { ALL_VIRTUAL_TAGS } from '@/shared/config/navigation';
import { parseSearchQuery } from '@/shared/lib/searchTokenizer';
import type { SearchParams } from '@/features/search/hooks/useSearchParams';
import { searchKeys } from '@/features/search/lib/queryKeys';

interface PreferenceTagState {
  includeTags: string[];
  excludeTags: string[];
}

function mergeUnique(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

interface UseSearchAutocompleteOptions {
  params: SearchParams;
  preferences: UserPreferencesResponse | null | undefined;
  preferenceTagState: PreferenceTagState;
  searchInput: string;
  debouncedQuery: string;
  showSuggestions: boolean;
}

export function useSearchAutocomplete({
  params,
  preferences,
  preferenceTagState,
  searchInput,
  debouncedQuery,
  showSuggestions,
}: UseSearchAutocompleteOptions) {
  const activeVirtualTag = useMemo(() => {
    const tokens = parseSearchQuery(searchInput || '');
    const tagToken = tokens.find((token) => token.type === 'tag' && token.mode === 'include');
    if (!tagToken) return null;
    return ALL_VIRTUAL_TAGS.find((virtualTag) => virtualTag.name === tagToken.value) ?? null;
  }, [searchInput]);

  const { data: filterMeta } = useQuery({
    queryKey: searchKeys.filterMeta(params.channel),
    queryFn: () =>
      searchApi.search({
        channel_ids: params.channel ? [params.channel] : undefined,
        limit: 1,
      }),
    staleTime: 5 * 60 * 1000,
  });

  const { data: channelTagCatalog = [] } = useQuery({
    queryKey: searchKeys.channelTagCatalog(),
    queryFn: () => searchApi.getChannelTagCatalog(),
    enabled: !params.channel,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const globalAvailableTags = useMemo(() => {
    const tagSet = new Set<string>();
    for (const channel of channelTagCatalog) {
      for (const tag of channel.available_tags || []) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
      for (const tag of channel.virtual_tags || []) {
        if (tag?.trim()) tagSet.add(tag.trim());
      }
    }
    return Array.from(tagSet);
  }, [channelTagCatalog]);

  const virtualTagOriginChannelMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const channel of channelTagCatalog) {
      for (const tag of channel.virtual_tags || []) {
        if (tag?.trim() && !map.has(tag.trim())) {
          map.set(tag.trim(), channel.channel_id);
        }
      }
    }
    return map;
  }, [channelTagCatalog]);

  const availableTags = useMemo(() => {
    return mergeUnique([
      ...(filterMeta?.virtual_tags || []),
      ...(filterMeta?.available_tags || []),
      ...globalAvailableTags,
      ...params.includeTags,
      ...params.excludeTags,
    ]);
  }, [filterMeta?.available_tags, filterMeta?.virtual_tags, globalAvailableTags, params.includeTags, params.excludeTags]);

  const discoveryPreferenceContext = useMemo(
    () => getDiscoveryPreferenceContext(preferences),
    [preferences],
  );

  const mergedTagState = useMemo(
    () =>
      mergePreferenceTagsWithManual({
        manualIncludeTags: params.includeTags,
        manualExcludeTags: params.excludeTags,
        preferenceIncludeTags: preferenceTagState.includeTags,
        preferenceExcludeTags: preferenceTagState.excludeTags,
        syncPreferenceTags: true,
      }),
    [params.includeTags, params.excludeTags, preferenceTagState.excludeTags, preferenceTagState.includeTags],
  );

  const preferenceSuggestedTags = useMemo(() => {
    const preferredChannels = new Set(discoveryPreferenceContext?.preferredChannelIds || []);
    const includeTags = preferenceTagState.includeTags;
    const excludeTags = new Set(preferenceTagState.excludeTags);

    const scopedCatalog = preferredChannels.size > 0
      ? channelTagCatalog.filter((channel) => preferredChannels.has(channel.channel_id))
      : channelTagCatalog;

    const collected = new Set<string>();

    for (const tag of includeTags) {
      if (!excludeTags.has(tag)) collected.add(tag);
    }

    for (const channel of scopedCatalog) {
      for (const tag of [...(channel.virtual_tags || []), ...(channel.available_tags || [])]) {
        const normalized = tag.trim();
        if (!normalized || excludeTags.has(normalized)) continue;
        collected.add(normalized);
      }
    }

    return Array.from(collected).slice(0, 8);
  }, [channelTagCatalog, discoveryPreferenceContext?.preferredChannelIds, preferenceTagState.excludeTags, preferenceTagState.includeTags]);

  const suggestionPreferencePatch = useMemo(
    () =>
      resolveDiscoveryPreferencePatch({
        preferences,
        mode: 'suggestion',
        query: searchInput,
        selectedChannel: params.channel,
      }),
    [preferences, searchInput, params.channel],
  );

  const { data: suggestionSearchData } = useQuery({
    queryKey: searchKeys.suggestions({
      query: debouncedQuery,
      channel: params.channel,
      preferenceSignature: discoveryPreferenceContext?.signature,
      channelIds: suggestionPreferencePatch?.channel_ids,
      includeTags: suggestionPreferencePatch?.include_tags,
      excludeTags: suggestionPreferencePatch?.exclude_tags,
    }),
    queryFn: () =>
      searchApi.search({
        query: debouncedQuery,
        channel_ids: params.channel ? [params.channel] : suggestionPreferencePatch?.channel_ids,
        include_tags: suggestionPreferencePatch?.include_tags,
        exclude_tags: suggestionPreferencePatch?.exclude_tags,
        limit: 5,
        sort_method: 'relevance',
      }),
    enabled: showSuggestions && debouncedQuery.length > 0,
    staleTime: 30 * 1000,
    retry: false,
  });

  const suggestionThreads = useMemo(() => {
    return (suggestionSearchData?.results || []).slice(0, 5).map((thread) => ({
      thread_id: thread.thread_id,
      title: thread.title,
      snippet: thread.first_message_excerpt || '',
      thumbnail_url: thread.thumbnail_urls?.[0] || null,
      author_name:
        thread.author?.display_name ||
        thread.author?.global_name ||
        thread.author?.name ||
        '未知用户',
      author_avatar_url: thread.author?.avatar_url || null,
      source_thread: thread,
    }));
  }, [suggestionSearchData?.results]);

  const suggestionAuthors = useMemo(() => {
    const unique = new Map<string, { id: string; name: string; avatar_url?: string | null }>();

    for (const thread of suggestionSearchData?.results || []) {
      if (!thread.author) continue;
      const authorId = String(thread.author.id);
      if (unique.has(authorId)) continue;

      unique.set(authorId, {
        id: authorId,
        name: thread.author.display_name || thread.author.global_name || thread.author.name,
        avatar_url: thread.author.avatar_url || null,
      });

      if (unique.size >= 5) break;
    }

    return Array.from(unique.values());
  }, [suggestionSearchData?.results]);

  const suggestionTags = useMemo(() => {
    return mergeUnique([
      ...(suggestionSearchData?.virtual_tags || []),
      ...(suggestionSearchData?.available_tags || []),
    ]).slice(0, 5);
  }, [suggestionSearchData?.available_tags, suggestionSearchData?.virtual_tags]);

  return {
    activeVirtualTag,
    availableTags,
    discoveryPreferenceContext,
    mergedTagState,
    preferenceSuggestedTags,
    suggestionAuthors,
    suggestionPreferencePatch,
    suggestionTags,
    suggestionThreads,
    virtualTagOriginChannelMap,
  };
}
