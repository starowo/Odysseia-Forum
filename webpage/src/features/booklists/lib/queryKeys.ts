export type BooklistScope = 'public' | 'mine' | 'collected';

export const booklistKeys = {
  all: ['booklists'] as const,
  lists: () => [...booklistKeys.all, 'list'] as const,
  list: (params: {
    scope: BooklistScope;
    keywords?: string;
    sortMethod: number;
    pageIndex: number;
    pageSize: number;
  }) => [...booklistKeys.lists(), params] as const,
  mineLists: () => [...booklistKeys.all, 'mine'] as const,
  detail: (booklistId: number) => [...booklistKeys.all, 'detail', booklistId] as const,
  items: (booklistId: number) => [...booklistKeys.all, 'items', booklistId] as const,
};
