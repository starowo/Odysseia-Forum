import { useCallback, useEffect, useRef, useState } from 'react';

import { mergePreferenceTagsWithManual } from '@/features/preferences/lib/discoveryPreferences';
import { addToken, parseSearchQuery, removeToken } from '@/shared/lib/searchTokenizer';
import type { SearchParams } from '@/features/search/hooks/useSearchParams';

interface UseTopBarFilterStateOptions {
  params: SearchParams;
  preferenceExcludeTags: string[];
  preferenceIncludeTags: string[];
  updateQuery: (nextQuery: string) => void;
  updateQueryFromTokenMutation: (mutator: (tokens: ReturnType<typeof parseSearchQuery>) => string) => void;
  virtualTagOriginChannelMap: Map<string, string>;
}

export function useTopBarFilterState({
  params,
  preferenceExcludeTags,
  preferenceIncludeTags,
  updateQuery,
  updateQueryFromTokenMutation,
  virtualTagOriginChannelMap,
}: UseTopBarFilterStateOptions) {
  const [syncPreferenceTags, setSyncPreferenceTags] = useState(false);
  const manualTagSnapshotRef = useRef<{ includeTags: string[]; excludeTags: string[] } | null>(null);

  useEffect(() => {
    if (!params.includeTags.length && !params.excludeTags.length) {
      setSyncPreferenceTags(false);
    }
  }, [params.includeTags.length, params.excludeTags.length]);

  const applyTagStateToQuery = useCallback(
    (nextIncludeTags: string[], nextExcludeTags: string[]) => {
      const currentTokens = parseSearchQuery(params.query || '');
      let nextQuery = params.query || '';

      for (const token of currentTokens) {
        if (token.type !== 'tag') continue;
        nextQuery = removeToken(nextQuery, token);
      }

      for (const tag of nextIncludeTags) {
        nextQuery = addToken(nextQuery, 'tag', tag, 'include');
      }

      for (const tag of nextExcludeTags) {
        nextQuery = addToken(nextQuery, 'tag', tag, 'exclude');
      }

      updateQuery(nextQuery.trim());
    },
    [params.query, updateQuery],
  );

  const handlePreferenceTagSyncToggle = useCallback(() => {
    const nextEnabled = !syncPreferenceTags;
    setSyncPreferenceTags(nextEnabled);

    if (nextEnabled) {
      manualTagSnapshotRef.current = {
        includeTags: [...params.includeTags],
        excludeTags: [...params.excludeTags],
      };

      const merged = mergePreferenceTagsWithManual({
        manualIncludeTags: params.includeTags,
        manualExcludeTags: params.excludeTags,
        preferenceIncludeTags,
        preferenceExcludeTags,
        syncPreferenceTags: true,
      });
      applyTagStateToQuery(merged.includeTags, merged.excludeTags);
      return;
    }

    const snapshot = manualTagSnapshotRef.current;
    manualTagSnapshotRef.current = null;
    applyTagStateToQuery(snapshot?.includeTags || [], snapshot?.excludeTags || []);
  }, [applyTagStateToQuery, params.excludeTags, params.includeTags, preferenceExcludeTags, preferenceIncludeTags, syncPreferenceTags]);

  const toggleTagToken = useCallback(
    (tagName: string, mode: 'include' | 'exclude') => {
      updateQueryFromTokenMutation((tokens) => {
        const existing = tokens.find(
          (token) => token.type === 'tag' && token.value === tagName && token.mode === mode,
        );
        const virtualOriginChannelId = !params.channel
          ? virtualTagOriginChannelMap.get(tagName) || null
          : null;

        let nextQuery = params.query || '';
        if (existing) {
          nextQuery = removeToken(nextQuery, existing);
          if (virtualOriginChannelId) {
            const nextTokens = parseSearchQuery(nextQuery);
            const hasOtherVirtualFromSameOrigin = nextTokens.some(
              (token) =>
                token.type === 'tag' &&
                token.mode === 'include' &&
                virtualTagOriginChannelMap.get(token.value) === virtualOriginChannelId,
            );
            if (!hasOtherVirtualFromSameOrigin) {
              const channelToken = nextTokens.find(
                (token) =>
                  token.type === 'channel' &&
                  token.mode === 'include' &&
                  token.value === virtualOriginChannelId,
              );
              if (channelToken) {
                nextQuery = removeToken(nextQuery, channelToken);
              }
            }
          }
        } else {
          const opposite = tokens.find(
            (token) => token.type === 'tag' && token.value === tagName && token.mode !== mode,
          );
          if (opposite) {
            nextQuery = removeToken(nextQuery, opposite);
          }
          nextQuery = addToken(nextQuery, 'tag', tagName, mode);
          if (virtualOriginChannelId) {
            nextQuery = addToken(nextQuery, 'channel', virtualOriginChannelId, 'include');
          }
        }
        return nextQuery.trim();
      });
    },
    [params.channel, params.query, updateQueryFromTokenMutation, virtualTagOriginChannelMap],
  );

  return {
    handlePreferenceTagSyncToggle,
    syncPreferenceTags,
    toggleTagToken,
  };
}
