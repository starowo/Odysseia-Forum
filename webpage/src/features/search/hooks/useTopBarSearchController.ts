import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { NavigateFunction } from 'react-router-dom';

import {
  addSearchHistory,
  clearSearchHistory,
  getSearchHistory,
  removeSearchHistory,
} from '@/shared/lib/searchHistory';
import {
  addToken,
  parseSearchQuery,
  removeToken,
  type SearchToken,
} from '@/shared/lib/searchTokenizer';
import type { SearchParams } from '@/features/search/hooks/useSearchParams';

function tokenSignature(query: string) {
  return parseSearchQuery(query || '')
    .filter((token) => token.type !== 'text')
    .map((token) => `${token.mode || 'include'}:${token.type}:${token.value.trim()}`)
    .filter(Boolean)
    .sort()
    .join('|');
}

interface UseTopBarSearchControllerOptions {
  isSearchPage: boolean;
  navigate: NavigateFunction;
  params: SearchParams;
  setParams: (updates: Partial<SearchParams>) => void;
}

export function useTopBarSearchController({
  isSearchPage,
  navigate,
  params,
  setParams,
}: UseTopBarSearchControllerOptions) {
  const [searchInput, setSearchInput] = useState(params.query);
  const [debouncedQuery, setDebouncedQuery] = useState(params.query.trim());
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [includeAuthorDraft, setIncludeAuthorDraft] = useState('');
  const [excludeAuthorDraft, setExcludeAuthorDraft] = useState('');
  const [historyItems, setHistoryItems] = useState(() => getSearchHistory());

  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const closePanels = useCallback(() => {
    setShowSuggestions(false);
    setShowFilters(false);
  }, []);

  useEffect(() => {
    setSearchInput(params.query);
  }, [params.query]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(searchInput.trim());
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (showSuggestions) {
      setHistoryItems(getSearchHistory());
    }
  }, [showSuggestions]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        closePanels();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [closePanels]);

  const executeSearch = useCallback(
    (nextQuery: string) => {
      const trimmed = nextQuery.trim();
      setSearchInput(trimmed);

      if (!isSearchPage) {
        navigate(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : '/search');
      } else {
        setParams({ query: trimmed });
      }

      if (trimmed) {
        addSearchHistory(trimmed);
        setHistoryItems(getSearchHistory());
      }
      closePanels();
    },
    [closePanels, isSearchPage, navigate, setParams],
  );

  const applyInputChange = useCallback(
    (nextQuery: string) => {
      setSearchInput(nextQuery);

      const tokenChanged = tokenSignature(nextQuery) !== tokenSignature(params.query || '');
      if (!tokenChanged) return;

      const trimmed = nextQuery.trim();
      if (!isSearchPage) {
        navigate(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : '/search');
      } else {
        setParams({ query: trimmed });
      }
    },
    [isSearchPage, navigate, params.query, setParams],
  );

  const handleSearch = useCallback(() => {
    executeSearch(searchInput);
  }, [executeSearch, searchInput]);

  const toggleFilters = useCallback(() => {
    if (showFilters) {
      closePanels();
      return;
    }
    setShowSuggestions(false);
    setShowFilters(true);
  }, [closePanels, showFilters]);

  const handleInputFocus = useCallback(() => {
    setShowSuggestions(true);
    setShowFilters(false);
  }, []);

  const allQueryTokens = useMemo(() => parseSearchQuery(searchInput), [searchInput]);
  const includeAuthorTokens = useMemo(
    () => allQueryTokens.filter((token) => token.type === 'author' && token.mode === 'include'),
    [allQueryTokens],
  );
  const excludeAuthorTokens = useMemo(
    () => allQueryTokens.filter((token) => token.type === 'author' && token.mode === 'exclude'),
    [allQueryTokens],
  );

  const updateQuery = useCallback(
    (nextQuery: string) => {
      setSearchInput(nextQuery);
      setParams({ query: nextQuery });
    },
    [setParams],
  );

  const updateQueryFromTokenMutation = useCallback(
    (mutator: (tokens: SearchToken[]) => string) => {
      updateQuery(mutator(parseSearchQuery(params.query || '')));
    },
    [params.query, updateQuery],
  );

  const removeAuthorToken = useCallback(
    (token: SearchToken) => {
      updateQuery(removeToken(params.query || '', token).trim());
    },
    [params.query, updateQuery],
  );

  const submitAuthorDraft = useCallback(
    (mode: 'include' | 'exclude') => {
      const draft = (mode === 'include' ? includeAuthorDraft : excludeAuthorDraft).trim();
      if (!draft) return;

      updateQuery(addToken(params.query || '', 'author', draft, mode).trim());

      if (mode === 'include') {
        setIncludeAuthorDraft('');
      } else {
        setExcludeAuthorDraft('');
      }
    },
    [excludeAuthorDraft, includeAuthorDraft, params.query, updateQuery],
  );

  const clearFilters = useCallback(() => {
    setSearchInput('');
    setIncludeAuthorDraft('');
    setExcludeAuthorDraft('');
    setParams({
      query: '',
      sortMethod: 'last_active_desc',
      timeFrom: '',
      timeTo: '',
      tagLogic: 'and',
    });
  }, [setParams]);

  const removeHistoryItem = useCallback((query: string) => {
    removeSearchHistory(query);
    setHistoryItems(getSearchHistory());
  }, []);

  const clearHistory = useCallback(() => {
    clearSearchHistory();
    setHistoryItems([]);
  }, []);

  return {
    applyInputChange,
    clearFilters,
    clearHistory,
    closePanels,
    debouncedQuery,
    excludeAuthorDraft,
    excludeAuthorTokens,
    executeSearch,
    handleInputFocus,
    handleSearch,
    historyItems,
    includeAuthorDraft,
    includeAuthorTokens,
    isPanelOpen: showSuggestions || showFilters,
    removeAuthorToken,
    removeHistoryItem,
    searchContainerRef,
    searchInput,
    searchInputRef,
    setExcludeAuthorDraft,
    setIncludeAuthorDraft,
    setShowFilters,
    setShowSuggestions,
    showFilters,
    showSuggestions,
    submitAuthorDraft,
    updateQuery,
    updateQueryFromTokenMutation,
    toggleFilters,
  };
}
