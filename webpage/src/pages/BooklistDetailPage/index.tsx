import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, Edit3, Plus, RefreshCw, Star, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { ThreadResultsCollection } from '@/entities/thread/ThreadResultsCollection';
import { useAuth } from '@/features/auth/hooks/useAuth';
import type { Thread } from '@/entities/thread/types';
import {
  useAddBooklistItems,
  useBooklistDetail,
  useBooklistItems,
  useDeleteBooklist,
  useRemoveBooklistItems,
  useToggleBooklistCollection,
  useUpdateBooklist,
  useUpdateBooklistItem,
} from '@/features/booklists/hooks/useBooklistsData';
import type { BooklistItem } from '@/entities/booklist/types';
import { BooklistFormModal } from '@/features/booklists/components/BooklistFormModal';
import { AddThreadsToBooklistModal } from '@/features/booklists/components/AddThreadsToBooklistModal';
import { BooklistItemEditorModal } from '@/features/booklists/components/BooklistItemEditorModal';
import { usePreviewThread } from '@/features/search/hooks/usePreviewThread';

function toThread(item: BooklistItem): Thread {
  return {
    thread_id: item.thread_id,
    channel_id: item.channel_id,
    title: item.title,
    author: item.author,
    created_at: item.created_at,
    last_active_at: item.created_at,
    reaction_count: item.reaction_count,
    reply_count: item.reply_count,
    display_count: 0,
    first_message_excerpt: item.comment || null,
    tags: [],
    virtual_tags: [],
    thumbnail_urls: item.thumbnail_urls || [],
    collected_flag: item.collected_flag,
  };
}

export function BooklistDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { openPreview } = usePreviewThread();

  const booklistId = Number.parseInt(id || '', 10);
  const [showEdit, setShowEdit] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [editingItem, setEditingItem] = useState<BooklistItem | null>(null);

  const detailQuery = useBooklistDetail(booklistId);
  const itemsQuery = useBooklistItems(booklistId);

  const isOwner = useMemo(
    () => String(detailQuery.data?.owner_id ?? '') === String(user?.id ?? ''),
    [detailQuery.data?.owner_id, user?.id],
  );

  const updateMutation = useUpdateBooklist(booklistId, () => setShowEdit(false));
  const deleteMutation = useDeleteBooklist(() => navigate('/booklists'));
  const collectMutation = useToggleBooklistCollection();
  const addItemsMutation = useAddBooklistItems(booklistId, () => setShowAdd(false));
  const removeItemMutation = useRemoveBooklistItems(booklistId);
  const updateItemMutation = useUpdateBooklistItem(booklistId, () => setEditingItem(null));

  if (!Number.isFinite(booklistId)) {
    return <div className="p-8 text-sm text-[var(--od-error)]">无效书单 ID</div>;
  }

  if (detailQuery.isLoading || itemsQuery.isLoading) {
    return <div className="p-8 text-sm text-[var(--od-text-secondary)]">正在帮你加载书单...</div>;
  }

  if (detailQuery.isError || !detailQuery.data) {
    return <div className="p-8 text-sm text-[var(--od-error)]">书单加载出错了，可能不存在或已经被删除了</div>;
  }

  const booklist = detailQuery.data;
  const items = itemsQuery.data?.results ?? [];

  return (
    <>
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
        <div className="flex flex-col gap-4 border-b border-[var(--od-border)] pb-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <button
                type="button"
                onClick={() => navigate('/booklists')}
                className="mt-1 rounded-md border border-[var(--od-border)] p-2 text-[var(--od-text-secondary)] transition-colors hover:text-[var(--od-text-primary)]"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>

              <div>
                <h1 className="text-2xl font-bold tracking-tight text-[var(--od-text-primary)]">{booklist.title}</h1>
                <p className="mt-1 text-sm text-[var(--od-text-secondary)]">{booklist.description || '暂无简介'}</p>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-[var(--od-text-tertiary)]">
                  <span className="inline-flex items-center gap-1">
                    <BookOpen className="h-3.5 w-3.5" />
                    {booklist.item_count}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Star className="h-3.5 w-3.5" />
                    {booklist.collection_count}
                  </span>
                  <span>{booklist.is_public ? '公开书单' : '私有书单'}</span>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => detailQuery.refetch()}
                className="inline-flex items-center gap-1 rounded-md border border-[var(--od-border)] px-3 py-1.5 text-xs text-[var(--od-text-secondary)]"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </button>

              <button
                type="button"
                onClick={() => collectMutation.mutate({ id: booklistId, collected: Boolean(booklist.collected_flag) })}
                className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                  booklist.collected_flag
                    ? 'bg-[var(--od-accent)]/15 text-[var(--od-accent)]'
                    : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)]'
                }`}
              >
                {booklist.collected_flag ? '已收藏' : '收藏书单'}
              </button>

              {isOwner && (
                <>
                  <button
                    type="button"
                    onClick={() => setShowEdit(true)}
                    className="inline-flex items-center gap-1 rounded-md border border-[var(--od-border)] px-3 py-1.5 text-xs text-[var(--od-text-secondary)]"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    编辑
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAdd(true)}
                    className="inline-flex items-center gap-1 rounded-md bg-[var(--od-accent)] px-3 py-1.5 text-xs font-semibold text-white"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    添加帖子
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!window.confirm(`确认删除书单「${booklist.title}」？`)) return;
                      deleteMutation.mutate(booklistId);
                    }}
                    className="inline-flex items-center gap-1 rounded-md border border-[var(--od-border)] px-3 py-1.5 text-xs text-[var(--od-error)]"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    删除
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {items.length === 0 ? (
          <div className="rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] p-10 text-center">
            <p className="text-base font-semibold text-[var(--od-text-primary)]">书单里还没有帖子</p>
            <p className="mt-1 text-sm text-[var(--od-text-secondary)]">{isOwner ? '可以点右上角添加帖子，开始充实你的书单吧。' : '作者还在准备中，再等等看。'}</p>
          </div>
        ) : (
          <div className="flex flex-col space-y-od-list-gap">
            {items.map((item) => (
              <div key={`${item.booklist_item_id}-${item.thread_id}`} className="space-y-2">
                <ThreadResultsCollection
                  threads={[toThread(item)]}
                  onPreview={openPreview}
                  listClassName="flex flex-col"
                />
                <div className="rounded-lg border border-[var(--od-border)] bg-[var(--od-card)] px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span className="text-[var(--od-text-tertiary)]">排序权重: {item.display_order}</span>
                    {isOwner && (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setEditingItem(item)}
                          className="rounded border border-[var(--od-border)] px-2 py-1 text-[var(--od-text-secondary)]"
                        >
                          编辑条目
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const tid = Number.parseInt(item.thread_id, 10);
                            if (!Number.isFinite(tid)) {
                              toast.error('无效 thread_id，无法删除');
                              return;
                            }
                            removeItemMutation.mutate(tid);
                          }}
                          className="rounded border border-[var(--od-border)] px-2 py-1 text-[var(--od-error)]"
                        >
                          移除
                        </button>
                      </div>
                    )}
                  </div>
                  {item.comment && <p className="mt-2 text-sm text-[var(--od-text-secondary)]">推荐语: {item.comment}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <BooklistFormModal
        isOpen={showEdit}
        initialValue={booklist}
        submitting={updateMutation.isPending}
        onClose={() => setShowEdit(false)}
        onSubmit={(payload) => updateMutation.mutate({ payload })}
      />

      <AddThreadsToBooklistModal
        isOpen={showAdd}
        submitting={addItemsMutation.isPending}
        onClose={() => setShowAdd(false)}
        onSubmit={(items) => addItemsMutation.mutate(items)}
      />

      <BooklistItemEditorModal
        isOpen={Boolean(editingItem)}
        item={editingItem}
        submitting={updateItemMutation.isPending}
        onClose={() => setEditingItem(null)}
        onSubmit={(payload) => {
          if (!editingItem) return;
          const tid = Number.parseInt(editingItem.thread_id, 10);
          if (!Number.isFinite(tid)) {
            toast.error('无效 thread_id，无法更新');
            return;
          }
          updateItemMutation.mutate({ threadId: tid, payload });
        }}
      />

    </>
  );
}
