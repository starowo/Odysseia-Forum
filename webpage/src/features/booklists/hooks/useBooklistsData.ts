import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { booklistsApi } from '@/features/booklists/api/booklistsApi';
import { booklistKeys, type BooklistScope } from '@/features/booklists/lib/queryKeys';
import type { BooklistFormInput, BooklistItemAddInput, BooklistItemUpdateInput } from '@/entities/booklist/types';
import { extractErrorMessage, notifyError, notifySuccess } from '@/shared/lib/notify';

export function useBooklistsList(params: {
  scope: BooklistScope;
  keywords?: string;
  sortMethod: number;
  pageIndex: number;
  pageSize: number;
}) {
  return useQuery({
    queryKey: booklistKeys.list(params),
    queryFn: async () => {
      if (params.scope === 'public') {
        return booklistsApi.listPublic(params);
      }

      return booklistsApi.listMine({
        keywords: params.keywords,
        sortMethod: params.sortMethod,
        pageIndex: params.pageIndex,
        pageSize: params.pageSize,
        createByCurrentUser: params.scope === 'mine',
        collectByCurrentUser: params.scope === 'collected',
      });
    },
    staleTime: 60 * 1000,
  });
}

export function useMyBooklistsList() {
  return useQuery({
    queryKey: [...booklistKeys.mineLists(), 'mine'],
    queryFn: () =>
      booklistsApi.listMine({
        createByCurrentUser: true,
        pageIndex: 0,
        pageSize: 18,
        sortMethod: 5,
      }),
    staleTime: 60 * 1000,
  });
}

export function useCollectedBooklistsList() {
  return useQuery({
    queryKey: [...booklistKeys.mineLists(), 'collected'],
    queryFn: () =>
      booklistsApi.listMine({
        collectByCurrentUser: true,
        pageIndex: 0,
        pageSize: 18,
        sortMethod: 6,
      }),
    staleTime: 60 * 1000,
  });
}

export function useBooklistDetail(booklistId: number) {
  return useQuery({
    queryKey: booklistKeys.detail(booklistId),
    queryFn: () => booklistsApi.getDetail(booklistId),
    enabled: Number.isFinite(booklistId),
    staleTime: 60 * 1000,
  });
}

export function useBooklistItems(booklistId: number) {
  return useQuery({
    queryKey: booklistKeys.items(booklistId),
    queryFn: () => booklistsApi.listItems(booklistId, 0, 100),
    enabled: Number.isFinite(booklistId),
    staleTime: 60 * 1000,
  });
}

function useInvalidateBooklists() {
  const queryClient = useQueryClient();

  return (booklistId?: number) => {
    queryClient.invalidateQueries({ queryKey: booklistKeys.all });
    if (typeof booklistId === 'number' && Number.isFinite(booklistId)) {
      queryClient.invalidateQueries({ queryKey: booklistKeys.detail(booklistId) });
      queryClient.invalidateQueries({ queryKey: booklistKeys.items(booklistId) });
    }
  };
}

export function useToggleBooklistCollection() {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: ({ id, collected }: { id: number; collected: boolean }) =>
      collected ? booklistsApi.uncollect([id]) : booklistsApi.collect([id]),
    onSuccess: (_, variables) => {
      invalidateBooklists(variables.id);
    },
    onError: (error) => notifyError(extractErrorMessage(error, '书单收藏状态更新失败')),
  });
}

export function useCreateBooklist(onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (payload: BooklistFormInput) => booklistsApi.create(payload),
    onSuccess: () => {
      notifySuccess('书单创建成功');
      invalidateBooklists();
      onSuccess?.();
    },
    onError: (error) => notifyError(extractErrorMessage(error, '书单创建失败')),
  });
}

export function useUpdateBooklist(booklistId?: number, onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: ({ id, payload }: { id?: number; payload: Partial<BooklistFormInput> }) =>
      booklistsApi.update(id ?? booklistId!, payload),
    onSuccess: (_, variables) => {
      notifySuccess('书单已更新');
      invalidateBooklists(variables.id ?? booklistId);
      onSuccess?.();
    },
    onError: (error) => notifyError(extractErrorMessage(error, '书单更新失败')),
  });
}

export function useDeleteBooklist(onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (id: number) => booklistsApi.remove(id),
    onSuccess: (_, id) => {
      notifySuccess('书单已删除');
      invalidateBooklists(id);
      onSuccess?.();
    },
    onError: (error) => notifyError(extractErrorMessage(error, '删除书单失败')),
  });
}

export function useAddBooklistItems(booklistId: number, onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (items: BooklistItemAddInput[]) => booklistsApi.addItems(booklistId, items),
    onSuccess: () => {
      notifySuccess('帖子已加入书单');
      invalidateBooklists(booklistId);
      onSuccess?.();
    },
    onError: (error) => notifyError(extractErrorMessage(error, '添加帖子到书单失败')),
  });
}

export function useRemoveBooklistItems(booklistId: number) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (threadId: number) => booklistsApi.removeItems(booklistId, [threadId]),
    onSuccess: () => {
      notifySuccess('书单条目已移除');
      invalidateBooklists(booklistId);
    },
    onError: (error) => notifyError(extractErrorMessage(error, '移除书单条目失败')),
  });
}

export function useUpdateBooklistItem(booklistId: number, onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: ({ threadId, payload }: { threadId: number; payload: BooklistItemUpdateInput }) =>
      booklistsApi.updateItem(booklistId, threadId, payload),
    onSuccess: () => {
      notifySuccess('书单条目已更新');
      invalidateBooklists(booklistId);
      onSuccess?.();
    },
    onError: (error) => notifyError(extractErrorMessage(error, '更新书单条目失败')),
  });
}
