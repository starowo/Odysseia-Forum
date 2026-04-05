import { BookOpen, Eye, Globe, Lock, Pencil, Star, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { Booklist } from '@/entities/booklist/types';

interface BooklistCardProps {
  booklist: Booklist;
  canManage: boolean;
  onOpen: (booklistId: number) => void;
  onToggleCollect: (booklist: Booklist) => void;
  onEdit: (booklist: Booklist) => void;
  onDelete: (booklist: Booklist) => void;
  collectLoading?: boolean;
}

export function BooklistCard({
  booklist,
  canManage,
  onOpen,
  onToggleCollect,
  onEdit,
  onDelete,
  collectLoading,
}: BooklistCardProps) {
  const updatedText = formatDistanceToNow(new Date(booklist.updated_at), {
    addSuffix: true,
    locale: zhCN,
  });

  return (
    <article
      className="group flex cursor-pointer flex-col gap-4 border-b border-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)] pb-5 transition-colors"
      onClick={() => onOpen(booklist.id)}
    >
      <div className="flex gap-4">
        <div className="relative h-28 w-24 shrink-0 overflow-hidden rounded-[1.35rem] bg-[color-mix(in_srgb,var(--od-surface-content)_64%,transparent)] sm:h-32 sm:w-28">
          {booklist.cover_image_url ? (
            <img
              src={booklist.cover_image_url}
              alt={booklist.title}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <BookOpen className="h-8 w-8 text-[var(--od-text-tertiary)]" />
            </div>
          )}
        </div>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            <span className="inline-flex items-center gap-1 text-[var(--od-text-tertiary)]">
              {booklist.is_public ? <Globe className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
              <span>{booklist.is_public ? '公开' : '私有'}</span>
            </span>
            <span className="text-[var(--od-text-tertiary)]/55">•</span>
            <span className="text-[var(--od-text-tertiary)]">更新于 {updatedText}</span>
          </div>

          <h3 className="mt-2 line-clamp-2 text-base font-semibold tracking-tight text-[var(--od-text-primary)] transition-colors group-hover:text-[var(--od-accent)]">
            {booklist.title}
          </h3>
          <p className="mt-2 line-clamp-3 text-sm leading-6 text-[var(--od-text-secondary)]">
            {booklist.description || '暂无简介'}
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] text-[var(--od-text-secondary)]">
            <span className="inline-flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5 text-[var(--od-text-tertiary)]" />
              <span className="text-[var(--od-accent)]">{booklist.item_count}</span>
              <span>帖子</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Star className="h-3.5 w-3.5 text-[var(--od-text-tertiary)]" />
              <span className="text-[var(--od-accent)]">{booklist.collection_count}</span>
              <span>收藏</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Eye className="h-3.5 w-3.5 text-[var(--od-text-tertiary)]" />
              <span className="text-[var(--od-accent)]">{booklist.view_count}</span>
              <span>浏览</span>
            </span>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[color-mix(in_srgb,var(--od-text-secondary)_12%,transparent)] pt-4">
          <button
            type="button"
            disabled={collectLoading}
            onClick={(e) => {
              e.stopPropagation();
              onToggleCollect(booklist);
            }}
            className={`od-inline-action ${
              booklist.collected_flag
                ? 'bg-[var(--od-accent)]/12 text-[var(--od-accent)] hover:bg-[var(--od-accent)]/16'
                : 'od-inline-action-ghost text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
            }`}
          >
            {booklist.collected_flag ? '已收藏' : '收藏'}
          </button>

          {canManage && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(booklist);
                }}
                className="od-inline-action od-inline-action-ghost px-2.5 text-[var(--od-text-tertiary)] hover:text-[var(--od-text-primary)]"
              >
                <Pencil className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(booklist);
                }}
                className="od-inline-action od-inline-action-ghost px-2.5 text-[var(--od-text-tertiary)] hover:text-[var(--od-error)]"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
      </div>
    </article>
  );
}
