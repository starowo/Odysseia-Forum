import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { booklistsApi } from '@/features/booklists/api/booklistsApi';
import { booklistKeys, type BooklistScope } from '@/features/booklists/lib/queryKeys';
import type { BooklistFormInput, BooklistItemAddInput, BooklistItemUpdateInput } from '@/entities/booklist/types';

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
    onError: () => toast.error('收藏状态更新失败'),
  });
}

export function useCreateBooklist(onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (payload: BooklistFormInput) => booklistsApi.create(payload),
    onSuccess: () => {
      toast.success('书单创建成功');
      invalidateBooklists();
      onSuccess?.();
    },
    onError: () => toast.error('书单创建失败'),
  });
}

export function useUpdateBooklist(booklistId?: number, onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: ({ id, payload }: { id?: number; payload: Partial<BooklistFormInput> }) =>
      booklistsApi.update(id ?? booklistId!, payload),
    onSuccess: (_, variables) => {
      toast.success('书单已更新');
      invalidateBooklists(variables.id ?? booklistId);
      onSuccess?.();
    },
    onError: () => toast.error('更新失败'),
  });
}

export function useDeleteBooklist(onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (id: number) => booklistsApi.remove(id),
    onSuccess: (_, id) => {
      toast.success('书单已删除');
      invalidateBooklists(id);
      onSuccess?.();
    },
    onError: () => toast.error('删除失败'),
  });
}

export function useAddBooklistItems(booklistId: number, onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (items: BooklistItemAddInput[]) => booklistsApi.addItems(booklistId, items),
    onSuccess: () => {
      toast.success('帖子已加入书单');
      invalidateBooklists(booklistId);
      onSuccess?.();
    },
    onError: () => toast.error('添加失败'),
  });
}

export function useRemoveBooklistItems(booklistId: number) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: (threadId: number) => booklistsApi.removeItems(booklistId, [threadId]),
    onSuccess: () => {
      toast.success('已移除条目');
      invalidateBooklists(booklistId);
    },
    onError: () => toast.error('移除失败'),
  });
}

export function useUpdateBooklistItem(booklistId: number, onSuccess?: () => void) {
  const invalidateBooklists = useInvalidateBooklists();

  return useMutation({
    mutationFn: ({ threadId, payload }: { threadId: number; payload: BooklistItemUpdateInput }) =>
      booklistsApi.updateItem(booklistId, threadId, payload),
    onSuccess: () => {
      toast.success('条目已更新');
      invalidateBooklists(booklistId);
      onSuccess?.();
    },
    onError: () => toast.error('更新条目失败'),
  });
}
