import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type SortMethod =
  | 'relevance'
  | 'last_active_desc'
  | 'created_desc'
  | 'reply_desc'
  | 'reaction_desc';

export type TagState = 'included' | 'excluded';

interface SearchState {
  // 搜索参数
  query: string;
  selectedChannel: string | null;
  sortMethod: SortMethod;
  tagLogic: 'and' | 'or';
  tagMode: 'included' | 'excluded';
  tagStates: Map<string, TagState>;
  timeFrom: Date | null;
  timeTo: Date | null;

  // 分页
  page: number;
  perPage: number;

  // Actions
  setQuery: (query: string) => void;
  setChannel: (channelId: string | null) => void;
  setSortMethod: (method: SortMethod) => void;
  setTagLogic: (logic: 'and' | 'or') => void;
  setTagMode: (mode: 'included' | 'excluded') => void;
  toggleTag: (tag: string) => void;
  clearTag: (tag: string) => void;
  clearAllTags: () => void;
  setTimeRange: (from: Date | null, to: Date | null) => void;
  setPage: (page: number) => void;
  setPerPage: (perPage: number) => void;
  clearFilters: () => void;
}

export const useSearchStore = create<SearchState>()(
  persist(
    (set) => ({
      // 初始状态
      query: '',
      selectedChannel: null,
      sortMethod: 'last_active_desc',
      tagLogic: 'and',
      tagMode: 'included',
      tagStates: new Map(),
      timeFrom: null,
      timeTo: null,
      page: 1,
      perPage: 24,

      // Actions
      setQuery: (query) => set({ query, page: 1 }),

      setChannel: (channelId) => set({ selectedChannel: channelId, page: 1 }),

      setSortMethod: (method) => set({ sortMethod: method, page: 1 }),

      setTagLogic: (logic) => set({ tagLogic: logic, page: 1 }),

      setTagMode: (mode) => set({ tagMode: mode }),

      toggleTag: (tag) =>
        set((state) => {
          const newTagStates = new Map(state.tagStates);
          const current = newTagStates.get(tag);

          if (current === state.tagMode) {
            newTagStates.delete(tag);
          } else {
            newTagStates.set(tag, state.tagMode);
          }

          return { tagStates: newTagStates, page: 1 };
        }),

      clearTag: (tag) =>
        set((state) => {
          const newTagStates = new Map(state.tagStates);
          newTagStates.delete(tag);
          return { tagStates: newTagStates };
        }),

      clearAllTags: () => set({ tagStates: new Map(), page: 1 }),

      setTimeRange: (from, to) => set({ timeFrom: from, timeTo: to, page: 1 }),

      setPage: (page) => set({ page }),

      setPerPage: (perPage) => set({ perPage, page: 1 }),

      clearFilters: () =>
        set({
          query: '',
          selectedChannel: null,
          tagStates: new Map(),
          timeFrom: null,
          timeTo: null,
          page: 1,
        }),
    }),
    {
      name: 'search-storage',
      partialize: (state) => ({
        sortMethod: state.sortMethod,
        perPage: state.perPage,
        tagLogic: state.tagLogic,
      }),
    }
  )
);
