import { useMemo, useState } from 'react';
import { Loader2, Plus, X } from 'lucide-react';
import type { BooklistItemAddInput } from '@/entities/booklist/types';

interface AddThreadsToBooklistModalProps {
  isOpen: boolean;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (items: BooklistItemAddInput[]) => void;
}

function parseThreadIds(raw: string): number[] {
  const segments = raw
    .split(/[\n,\s]+/g)
    .map((part) => part.trim())
    .filter(Boolean);
  const ids = segments
    .map((part) => Number.parseInt(part, 10))
    .filter((num) => Number.isFinite(num) && num > 0);
  return Array.from(new Set(ids));
}

export function AddThreadsToBooklistModal({
  isOpen,
  submitting,
  onClose,
  onSubmit,
}: AddThreadsToBooklistModalProps) {
  const [rawIds, setRawIds] = useState('');
  const [comment, setComment] = useState('');
  const [displayOrder, setDisplayOrder] = useState('');

  const parsedIds = useMemo(() => parseThreadIds(rawIds), [rawIds]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="od-floating-panel-solid w-full max-w-lg rounded-xl border border-[var(--od-border)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--od-border)] px-5 py-4">
          <h2 className="text-base font-bold text-[var(--od-text-primary)]">批量添加帖子</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">
              Thread ID 列表（逗号/空格/换行分隔）
            </label>
            <textarea
              value={rawIds}
              onChange={(e) => setRawIds(e.target.value)}
              rows={6}
              placeholder="123456789012345678\n987654321098765432"
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
            />
            <p className="mt-1 text-xs text-[var(--od-text-tertiary)]">可解析 {parsedIds.length} 个 ID</p>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">统一备注（可选）</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">
              起始排序权重（可选）
            </label>
            <input
              type="number"
              value={displayOrder}
              onChange={(e) => setDisplayOrder(e.target.value)}
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
            />
          </div>

          <div className="flex justify-end gap-2 border-t border-[var(--od-border)] pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-2 text-sm text-[var(--od-text-secondary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
            >
              取消
            </button>
            <button
              type="button"
              disabled={submitting || parsedIds.length === 0}
              onClick={() => {
                const orderStart = Number.parseInt(displayOrder, 10);
                const hasOrder = Number.isFinite(orderStart);
                const items = parsedIds.map((id, index) => ({
                  thread_id: id,
                  comment: comment.trim() || undefined,
                  display_order: hasOrder ? orderStart + index : undefined,
                }));
                onSubmit(items);
              }}
              className="inline-flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--od-accent-hover)] disabled:opacity-60"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              添加到书单
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
