import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Plus, RefreshCw, Search, SlidersHorizontal } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { useAuth } from '@/features/auth/hooks/useAuth';
import { BooklistCard } from '@/entities/booklist/BooklistCard';
import type { Booklist, BooklistFormInput } from '@/entities/booklist/types';
import { booklistsApi } from '@/features/booklists/api/booklistsApi';
import { BooklistFormModal } from '@/features/booklists/components/BooklistFormModal';

type BooklistScope = 'public' | 'mine' | 'collected';

const scopeOptions: Array<{ key: BooklistScope; label: string }> = [
  { key: 'public', label: '公开书单' },
  { key: 'mine', label: '我的创建' },
  { key: 'collected', label: '我的收藏' },
];

export function BooklistsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [scope, setScope] = useState<BooklistScope>('public');
  const [keywords, setKeywords] = useState('');
  const [sortMethod, setSortMethod] = useState<number>(4);
  const [pageIndex, setPageIndex] = useState(0);

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Booklist | null>(null);

  const listQuery = useQuery({
    queryKey: ['booklists', scope, keywords, sortMethod, pageIndex],
    queryFn: async () => {
      if (scope === 'public') {
        return booklistsApi.listPublic({
          keywords: keywords || undefined,
          sortMethod,
          pageIndex,
          pageSize: 12,
        });
      }

      if (scope === 'mine') {
        return booklistsApi.listMine({
          createByCurrentUser: true,
          keywords: keywords || undefined,
          sortMethod,
          pageIndex,
          pageSize: 12,
        });
      }

      return booklistsApi.listMine({
        collectByCurrentUser: true,
        keywords: keywords || undefined,
        sortMethod,
        pageIndex,
        pageSize: 12,
      });
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: BooklistFormInput) => booklistsApi.create(payload),
    onSuccess: () => {
      toast.success('书单创建成功');
      setShowCreate(false);
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
    },
    onError: () => {
      toast.error('书单创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: BooklistFormInput }) =>
      booklistsApi.update(id, payload),
    onSuccess: () => {
      toast.success('书单已更新');
      setEditing(null);
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
    },
    onError: () => {
      toast.error('更新失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => booklistsApi.remove(id),
    onSuccess: () => {
      toast.success('书单已删除');
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
    },
    onError: () => {
      toast.error('删除失败');
    },
  });

  const collectMutation = useMutation({
    mutationFn: ({ id, collected }: { id: number; collected: boolean }) =>
      collected ? booklistsApi.uncollect([id]) : booklistsApi.collect([id]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['booklists'] });
      queryClient.invalidateQueries({ queryKey: ['booklist-detail'] });
    },
    onError: () => {
      toast.error('收藏状态更新失败');
    },
  });

  const results = listQuery.data?.results ?? [];
  const total = listQuery.data?.total ?? 0;
  const pageSize = listQuery.data?.limit ?? 12;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const sortOptions = useMemo(
    () => [
      { value: 1, label: '按帖子数' },
      { value: 2, label: '按浏览数' },
      { value: 3, label: '按收藏数' },
      { value: 4, label: '按创建时间' },
      { value: 5, label: '按更新时间' },
      ...(scope === 'collected' ? [{ value: 6, label: '按收藏时间' }] : []),
    ],
    [scope],
  );

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col gap-3 border-b border-[var(--od-border)] pb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--od-accent)]/10 text-[var(--od-accent)] shadow-inner">
              <BookOpen className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">书单</h1>
              <p className="text-sm text-[var(--od-text-secondary)]">管理、收藏、维护你的帖子索引合集</p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--od-accent-hover)]"
          >
            <Plus className="h-4 w-4" />
            新建书单
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {scopeOptions.map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => {
                setScope(option.key);
                setPageIndex(0);
              }}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                scope === option.key
                  ? 'bg-[var(--od-accent)] text-white'
                  : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
          <div className="flex items-center gap-2 rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3">
            <Search className="h-4 w-4 text-[var(--od-text-tertiary)]" />
            <input
              value={keywords}
              onChange={(e) => {
                setKeywords(e.target.value);
                setPageIndex(0);
              }}
              placeholder="搜索书单标题或简介"
              className="h-10 w-full bg-transparent text-sm text-[var(--od-text-primary)] outline-none placeholder:text-[var(--od-text-tertiary)]"
            />
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3">
            <SlidersHorizontal className="h-4 w-4 text-[var(--od-text-tertiary)]" />
            <select
              value={sortMethod}
              onChange={(e) => {
                setSortMethod(Number.parseInt(e.target.value, 10));
                setPageIndex(0);
              }}
              className="h-10 bg-transparent text-sm text-[var(--od-text-primary)] outline-none"
            >
              {sortOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => listQuery.refetch()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 text-sm text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
          >
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        </div>
      </div>

      {listQuery.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="h-72 animate-pulse rounded-xl bg-[var(--od-bg-tertiary)]" />
          ))}
        </div>
      ) : listQuery.isError ? (
        <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-8 text-center text-sm text-[var(--od-text-secondary)]">
          书单加载失败，请稍后重试。
        </div>
      ) : results.length === 0 ? (
        <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-10 text-center">
          <p className="text-base font-semibold text-[var(--od-text-primary)]">暂无书单</p>
          <p className="mt-1 text-sm text-[var(--od-text-secondary)]">
            {scope === 'public' ? '还没有可见的公开书单。' : '你还没有对应书单，先创建一个吧。'}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {results.map((booklist) => (
              <BooklistCard
                key={booklist.id}
                booklist={booklist}
                canManage={String(booklist.owner_id) === String(user?.id)}
                onOpen={(id) => navigate(`/booklists/${id}`)}
                onToggleCollect={(item) =>
                  collectMutation.mutate({ id: item.id, collected: Boolean(item.collected_flag) })
                }
                onEdit={(item) => setEditing(item)}
                onDelete={(item) => {
                  if (!window.confirm(`确认删除书单「${item.title}」？`)) return;
                  deleteMutation.mutate(item.id);
                }}
                collectLoading={collectMutation.isPending}
              />
            ))}
          </div>

          <div className="flex items-center justify-between rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] px-4 py-3 text-sm">
            <span className="text-[var(--od-text-secondary)]">
              第 {pageIndex + 1} / {totalPages} 页，共 {total} 条
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPageIndex((prev) => Math.max(0, prev - 1))}
                disabled={pageIndex === 0}
                className="rounded border border-[var(--od-border)] px-3 py-1 text-[var(--od-text-secondary)] disabled:opacity-40"
              >
                上一页
              </button>
              <button
                type="button"
                onClick={() => setPageIndex((prev) => (prev + 1 < totalPages ? prev + 1 : prev))}
                disabled={pageIndex + 1 >= totalPages}
                className="rounded border border-[var(--od-border)] px-3 py-1 text-[var(--od-text-secondary)] disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}

      <BooklistFormModal
        isOpen={showCreate}
        submitting={createMutation.isPending}
        onClose={() => setShowCreate(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
      />

      <BooklistFormModal
        isOpen={Boolean(editing)}
        initialValue={editing}
        submitting={updateMutation.isPending}
        onClose={() => setEditing(null)}
        onSubmit={(payload) => {
          if (!editing) return;
          updateMutation.mutate({ id: editing.id, payload });
        }}
      />
    </div>
  );
}
