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
      className="group flex cursor-pointer flex-col overflow-hidden rounded-xl border border-[var(--od-border)] bg-[var(--od-card)] shadow-sm transition-all hover:border-[var(--od-accent)]/40 hover:shadow-lg"
      onClick={() => onOpen(booklist.id)}
    >
      <div className="relative h-36 w-full overflow-hidden bg-[var(--od-bg-tertiary)]">
        {booklist.cover_image_url ? (
          <img
            src={booklist.cover_image_url}
            alt={booklist.title}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <BookOpen className="h-8 w-8 text-[var(--od-text-tertiary)]" />
          </div>
        )}
        <div className="absolute left-2 top-2 inline-flex items-center gap-1 rounded-full bg-black/45 px-2 py-0.5 text-[10px] text-white backdrop-blur-sm">
          {booklist.is_public ? <Globe className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
          <span>{booklist.is_public ? '公开' : '私有'}</span>
        </div>
      </div>

      <div className="flex flex-1 flex-col p-3">
        <h3 className="line-clamp-2 text-sm font-bold text-[var(--od-text-primary)]">{booklist.title}</h3>
        <p className="mt-1 line-clamp-2 min-h-[2.5rem] text-xs text-[var(--od-text-secondary)]">
          {booklist.description || '暂无简介'}
        </p>

        <div className="mt-2 grid grid-cols-3 gap-2 text-[11px] text-[var(--od-text-tertiary)]">
          <span className="inline-flex items-center gap-1">
            <BookOpen className="h-3.5 w-3.5" />
            {booklist.item_count}
          </span>
          <span className="inline-flex items-center gap-1">
            <Star className="h-3.5 w-3.5" />
            {booklist.collection_count}
          </span>
          <span className="inline-flex items-center gap-1">
            <Eye className="h-3.5 w-3.5" />
            {booklist.view_count}
          </span>
        </div>

        <p className="mt-2 text-[11px] text-[var(--od-text-tertiary)]">更新于 {updatedText}</p>

        <div className="mt-3 flex items-center justify-between gap-2 border-t border-[var(--od-border)] pt-3">
          <button
            type="button"
            disabled={collectLoading}
            onClick={(e) => {
              e.stopPropagation();
              onToggleCollect(booklist);
            }}
            className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              booklist.collected_flag
                ? 'bg-[var(--od-accent)]/15 text-[var(--od-accent)] hover:bg-[var(--od-accent)]/20'
                : 'bg-[var(--od-bg-tertiary)] text-[var(--od-text-secondary)] hover:text-[var(--od-text-primary)]'
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
                className="rounded p-1 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-text-primary)]"
              >
                <Pencil className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(booklist);
                }}
                className="rounded p-1 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-tertiary)] hover:text-[var(--od-error)]"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
