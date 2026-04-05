import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2, X } from 'lucide-react';
import type { Booklist, BooklistFormInput } from '@/entities/booklist/types';

const schema = z.object({
  title: z.string().trim().min(1, '请输入书单标题').max(80, '标题最多 80 字'),
  description: z.string().max(600, '简介最多 600 字').optional(),
  cover_image_url: z
    .string()
    .trim()
    .optional()
    .refine((value) => !value || /^https?:\/\//.test(value), '封面链接需以 http(s):// 开头'),
  is_public: z.boolean(),
  display_type: z.number().int().min(1).max(2),
});

type FormValues = z.infer<typeof schema>;

interface BooklistFormModalProps {
  isOpen: boolean;
  initialValue?: Booklist | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (payload: BooklistFormInput) => void;
}

export function BooklistFormModal({
  isOpen,
  initialValue,
  submitting,
  onClose,
  onSubmit,
}: BooklistFormModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '',
      description: '',
      cover_image_url: '',
      is_public: true,
      display_type: 1,
    },
  });

  useEffect(() => {
    if (!isOpen) return;
    reset({
      title: initialValue?.title ?? '',
      description: initialValue?.description ?? '',
      cover_image_url: initialValue?.cover_image_url ?? '',
      is_public: initialValue?.is_public ?? true,
      display_type: initialValue?.display_type ?? 1,
    });
  }, [initialValue, isOpen, reset]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="od-floating-panel-solid w-full max-w-xl rounded-xl border border-[var(--od-border)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--od-border)] px-5 py-4">
          <h2 className="text-base font-bold text-[var(--od-text-primary)]">
            {initialValue ? '编辑书单' : '创建书单'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--od-text-tertiary)] transition-colors hover:bg-[var(--od-bg-secondary)] hover:text-[var(--od-text-primary)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit((values) => onSubmit(values))} className="space-y-4 p-5">
          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">标题 *</label>
            <input
              {...register('title')}
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
              placeholder="输入书单标题"
            />
            {errors.title && <p className="mt-1 text-xs text-[var(--od-error)]">{errors.title.message}</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">简介</label>
            <textarea
              {...register('description')}
              rows={4}
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
              placeholder="写一段简介，说明这个书单的主题"
            />
            {errors.description && (
              <p className="mt-1 text-xs text-[var(--od-error)]">{errors.description.message}</p>
            )}
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">封面图链接</label>
            <input
              {...register('cover_image_url')}
              className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
              placeholder="https://..."
            />
            {errors.cover_image_url && (
              <p className="mt-1 text-xs text-[var(--od-error)]">{errors.cover_image_url.message}</p>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex items-center gap-2 rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-secondary)]">
              <input type="checkbox" {...register('is_public')} />
              公开书单
            </label>

            <div>
              <label className="mb-1 block text-xs font-semibold text-[var(--od-text-secondary)]">展示顺序</label>
              <select
                {...register('display_type', { valueAsNumber: true })}
                className="w-full rounded-lg border border-[var(--od-border)] bg-[var(--od-bg-secondary)] px-3 py-2 text-sm text-[var(--od-text-primary)] outline-none transition-colors focus:border-[var(--od-accent)]"
              >
                <option value={1}>按加入时间（新到旧）</option>
                <option value={2}>按自定义排序（display_order）</option>
              </select>
            </div>
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
              {initialValue ? '保存修改' : '创建书单'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
