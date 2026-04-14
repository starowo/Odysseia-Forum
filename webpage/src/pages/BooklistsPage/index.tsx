import { useMemo, useState } from 'react';
import { BookOpen, Plus, RefreshCw, Search, SlidersHorizontal } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/hooks/useAuth';
import { BooklistCard } from '@/entities/booklist/BooklistCard';
import type { Booklist } from '@/entities/booklist/types';
import {
  useBooklistsList,
  useCreateBooklist,
  useDeleteBooklist,
  useToggleBooklistCollection,
  useUpdateBooklist,
} from '@/features/booklists/hooks/useBooklistsData';
import { BooklistFormModal } from '@/features/booklists/components/BooklistFormModal';
import { FluidDivider } from '@/shared/ui/FluidDivider';

type BooklistScope = 'public' | 'mine' | 'collected';

const scopeOptions: Array<{ key: BooklistScope; label: string }> = [
  { key: 'public', label: '公开书单' },
  { key: 'mine', label: '我的创建' },
  { key: 'collected', label: '我的收藏' },
];

export function BooklistsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [scope, setScope] = useState<BooklistScope>('public');
  const [keywords, setKeywords] = useState('');
  const [sortMethod, setSortMethod] = useState<number>(4);
  const [pageIndex, setPageIndex] = useState(0);

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Booklist | null>(null);

  const listQuery = useBooklistsList({
    scope,
    keywords: keywords || undefined,
    sortMethod,
    pageIndex,
    pageSize: 12,
  });

  const createMutation = useCreateBooklist(() => setShowCreate(false));
  const updateMutation = useUpdateBooklist(undefined, () => setEditing(null));
  const deleteMutation = useDeleteBooklist();
  const collectMutation = useToggleBooklistCollection();

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
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-10 p-4 sm:p-6 lg:gap-14 lg:p-8">
      <section>
        <FluidDivider label="Booklists" tone="strong" className="mb-8 lg:mb-10" />
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--od-surface-soft)] text-[var(--od-accent)]">
                <BookOpen className="h-6 w-6" />
              </div>
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--od-text-tertiary)]">
                  内容整理
                </p>
                <div className="space-y-1.5">
                   <h1 className="od-section-title">书单</h1>
                   <p className="max-w-2xl text-sm leading-6 text-[var(--od-text-secondary)]">
                     喜欢的内容可以慢慢收进书单里呀。你可以自己偷偷留着，也可以整理好了再拿出来分享给别人看。
                   </p>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="od-inline-action od-inline-action-primary w-full justify-center sm:w-auto sm:self-start"
            >
              <Plus className="h-4 w-4" />
              新建书单
            </button>
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)] lg:items-start">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                {scopeOptions.map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => {
                      setScope(option.key);
                      setPageIndex(0);
                    }}
                    className={`od-pill-chip ${
                      scope === option.key
                        ? 'bg-[var(--od-accent)] text-white'
                        : 'text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <p className="text-sm leading-6 text-[var(--od-text-secondary)]">
                 你可以先看看公开的，或者翻翻自己整理过、收藏过的那些，再慢慢搜就好，不用急。
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] lg:grid-cols-1">
              <div className="flex items-center gap-2 rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4">
                <Search className="h-4 w-4 text-[var(--od-text-tertiary)]" />
                <input
                  value={keywords}
                  onChange={(e) => {
                    setKeywords(e.target.value);
                    setPageIndex(0);
                  }}
                  placeholder="搜索书单标题或简介"
                  className="h-11 w-full bg-transparent text-sm text-[var(--od-text-primary)] outline-none placeholder:text-[var(--od-text-tertiary)]"
                />
              </div>

              <div className="flex items-center gap-2 rounded-2xl border border-[var(--od-shell-line)] bg-[color-mix(in_srgb,var(--od-surface-input)_72%,transparent)] px-4">
                <SlidersHorizontal className="h-4 w-4 text-[var(--od-text-tertiary)]" />
                <select
                  value={sortMethod}
                  onChange={(e) => {
                    setSortMethod(Number.parseInt(e.target.value, 10));
                    setPageIndex(0);
                  }}
                  className="h-11 w-full bg-transparent text-sm text-[var(--od-text-primary)] outline-none"
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
                className="od-inline-action od-inline-action-ghost justify-center"
              >
                <RefreshCw className="h-4 w-4" />
                刷新
              </button>
            </div>
          </div>
        </div>
      </section>

      {listQuery.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, idx) => (
            <div key={idx} className="h-72 animate-pulse rounded-[1.35rem] bg-[color-mix(in_srgb,var(--od-surface-content)_62%,transparent)]" />
          ))}
        </div>
      ) : listQuery.isError ? (
        <div className="py-12 text-center text-sm text-[var(--od-text-secondary)]">
          书单这边刚刚有点小迷糊，等一下再来，我会重新帮你拿一遍的。
        </div>
      ) : results.length === 0 ? (
        <div className="py-14 text-center">
          <p className="text-base font-semibold text-[var(--od-text-primary)]">暂无书单</p>
          <p className="mt-1 text-sm text-[var(--od-text-secondary)]">
            {scope === 'public' ? '现在还没有公开书单呢，要不要顺手做第一个呀？' : '这里还空着呢，你可以慢慢新建一个试试。'}
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

          <div className="flex items-center justify-between border-t border-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)] pt-5 text-sm">
            <span className="text-[var(--od-text-secondary)]">
              第 {pageIndex + 1} / {totalPages} 页，共 {total} 条
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPageIndex((prev) => Math.max(0, prev - 1))}
                disabled={pageIndex === 0}
                className="od-inline-action od-inline-action-ghost disabled:opacity-40"
              >
                上一页
              </button>
              <button
                type="button"
                onClick={() => setPageIndex((prev) => (prev + 1 < totalPages ? prev + 1 : prev))}
                disabled={pageIndex + 1 >= totalPages}
                className="od-inline-action od-inline-action-ghost disabled:opacity-40"
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
