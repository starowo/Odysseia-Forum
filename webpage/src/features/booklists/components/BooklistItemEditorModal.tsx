import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2, X } from 'lucide-react';
import type { BooklistItem } from '@/entities/booklist/types';

const schema = z.object({
  comment: z.string().max(800, '备注最多 800 字').optional(),
  display_order: z
    .string()
    .optional()
    .refine((value) => !value || /^-?\d+$/.test(value), '排序权重必须是整数'),
});

type FormValues = z.infer<typeof schema>;

interface BooklistItemEditorModalProps {
  isOpen: boolean;
  item: BooklistItem | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: { comment?: string; display_order?: number }) => void;
}

export function BooklistItemEditorModal({
  isOpen,
  item,
  submitting,
  onClose,
  onSubmit,
}: BooklistItemEditorModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      comment: '',
      display_order: '',
    },
  });

  useEffect(() => {
    if (!isOpen || !item) return;
    reset({
      comment: item.comment ?? '',
      display_order: String(item.display_order ?? ''),
    });
  }, [isOpen, item, reset]);

  if (!isOpen || !item) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl border border-[var(--od-border)] bg-[var(--od-bg)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--od-border)] px-5 py-4">
          <h2 className="text-base font-bold text-[var(--od-text-primary)]">编辑书单项</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form
          onSubmit={handleSubmit((values) => {
            const order = values.display_order ? Number.parseInt(values.display_order, 10) : undefined;
            onSubmit({
              comment: values.comment?.trim() || undefined,
              display_order: Number.isFinite(order) ? order : undefined,
            });
          })}
          className="space-y-4 p-5"
        >
          <div>
            <p className="line-clamp-2 text-sm font-semibold text-[var(--od-text-primary)]">{item.title}</p>
            <p className="mt-1 text-xs text-[var(--od-text-tertiary)]">Thread ID: {item.thread_id}</p>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">备注</label>
            <textarea
              {...register('comment')}
              rows={5}
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
            />
            {errors.comment && <p className="mt-1 text-xs text-[var(--od-error)]">{errors.comment.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">排序权重</label>
            <input
              {...register('display_order')}
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
            />
            {errors.display_order && (
              <p className="mt-1 text-xs text-[var(--od-error)]">{errors.display_order.message}</p>
            )}
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
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-lg bg-[var(--od-accent)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--od-accent-hover)] disabled:opacity-60"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              保存
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
