import { useEffect, useMemo, useRef, useState } from 'react';

import { useInfiniteQuery } from '@tanstack/react-query';

import type { Thread } from '@/entities/thread/types';
import { searchApi } from '@/features/search/api/searchApi';
import {
  getDiscoveryPreferenceContext,
  resolveDiscoveryPreferencePatch,
} from '@/features/preferences/lib/discoveryPreferences';
import type { UserPreferencesResponse } from '@/features/preferences/api/preferencesApi';
import type { SearchParams } from '@/features/search/hooks/useSearchParams';
import { searchKeys } from '@/features/search/lib/queryKeys';

interface UseSearchResultsOptions {
  params: SearchParams;
  preferences: UserPreferencesResponse | null | undefined;
}

export function useSearchResults({ params, preferences }: UseSearchResultsOptions) {
  const {
    query,
    channel: selectedChannel,
    includeTags,
    excludeTags,
    includeAuthors,
    excludeAuthors,
    tagLogic,
    sortMethod,
    timeFrom,
    timeTo,
  } = params;

  const perPage = 24;
  const loadMoreRef = useRef<HTMLDivElement | null>(null);
  const [ignoreDiscoveryPreferences, setIgnoreDiscoveryPreferences] = useState(false);

  const hasExplicitFilters =
    includeTags.length > 0 ||
    excludeTags.length > 0 ||
    includeAuthors.length > 0 ||
    excludeAuthors.length > 0 ||
    !!timeFrom ||
    !!timeTo ||
    (sortMethod && sortMethod !== 'last_active_desc') ||
    (tagLogic && tagLogic !== 'and');

  const discoveryPreferenceContext = useMemo(
    () => getDiscoveryPreferenceContext(preferences),
    [preferences],
  );

  const discoveryPreferencePatch = useMemo(
    () =>
      ignoreDiscoveryPreferences
        ? null
        : resolveDiscoveryPreferencePatch({
            preferences,
            mode: 'browse-empty',
            query,
            selectedChannel,
            hasExplicitFilters,
          }),
    [preferences, query, selectedChannel, hasExplicitFilters, ignoreDiscoveryPreferences],
  );

  const effectiveSortMethod = discoveryPreferencePatch?.sort_method || sortMethod;
  const effectivePerPage = discoveryPreferencePatch?.limit || perPage;
  const effectiveChannelIds = selectedChannel ? [selectedChannel] : discoveryPreferencePatch?.channel_ids;
  const effectiveIncludeTags = includeTags.length > 0 ? includeTags : discoveryPreferencePatch?.include_tags || [];
  const effectiveExcludeTags = excludeTags.length > 0 ? excludeTags : discoveryPreferencePatch?.exclude_tags || [];

  useEffect(() => {
    if (query.trim() || selectedChannel || hasExplicitFilters) {
      setIgnoreDiscoveryPreferences(false);
    }
  }, [query, selectedChannel, hasExplicitFilters]);

  const queryState = useInfiniteQuery<any, Error, any, any, number>({
    queryKey: searchKeys.results({
      ...params,
      effectiveChannelIds,
      effectiveIncludeTags,
      effectiveExcludeTags,
      effectiveSortMethod,
      effectivePerPage,
      preferenceSignature: discoveryPreferenceContext?.signature,
    }),
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      searchApi.search({
        query: query || undefined,
        channel_ids: effectiveChannelIds,
        include_tags: effectiveIncludeTags,
        exclude_tags: effectiveExcludeTags,
        tag_logic: tagLogic,
        sort_method: effectiveSortMethod,
        limit: effectivePerPage,
        offset: Number(pageParam) || 0,
        created_after: timeFrom || undefined,
        created_before: timeTo || undefined,
      }),
    getNextPageParam: (lastPage, allPages) => {
      const loadedCount = allPages.reduce(
        (sum: number, page: Awaited<ReturnType<typeof searchApi.search>>) => sum + (page.results?.length || 0),
        0,
      );
      return loadedCount < (lastPage.total || 0) ? loadedCount : undefined;
    },
    staleTime: 30 * 1000,
  });

  const results = useMemo<Thread[]>(() => {
    const mergedResults =
      (queryState.data?.pages.flatMap(
        (page: Awaited<ReturnType<typeof searchApi.search>>) => page.results || [],
      ) || []) as Thread[];

    const uniqueResults = new Map<string, Thread>();
    for (const thread of mergedResults) {
      if (!thread?.thread_id) continue;
      if (!uniqueResults.has(thread.thread_id)) {
        uniqueResults.set(thread.thread_id, thread);
      }
    }

    return Array.from(uniqueResults.values());
  }, [queryState.data]);

  const totalResults = Number(queryState.data?.pages?.[0]?.total || 0);

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || !queryState.hasNextPage) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && queryState.hasNextPage && !queryState.isFetchingNextPage) {
          queryState.fetchNextPage();
        }
      },
      { rootMargin: '300px 0px' },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [queryState.fetchNextPage, queryState.hasNextPage, queryState.isFetchingNextPage, results.length]);

  const hasSearchFilters = !!query || hasExplicitFilters;
  const isPreferenceFilteredBrowse =
    !query.trim() && !selectedChannel && !hasExplicitFilters && Boolean(discoveryPreferencePatch);

  return {
    discoveryPreferenceContext,
    hasExplicitFilters,
    hasSearchFilters,
    ignoreDiscoveryPreferences,
    isPreferenceFilteredBrowse,
    loadMoreRef,
    queryState,
    results,
    setIgnoreDiscoveryPreferences,
    totalResults,
  };
}
