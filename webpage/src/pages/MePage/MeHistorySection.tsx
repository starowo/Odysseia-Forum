import { Eye, RefreshCw, Trash2 } from 'lucide-react';

import type { BrowseHistoryItem } from '@/shared/lib/browseHistory';
import { FluidDivider } from '@/shared/ui/FluidDivider';

interface MeHistorySectionProps {
  historyItems: BrowseHistoryItem[];
  onClear: () => void;
  onOpenThread: (threadId: string) => void;
  onRefresh: () => void;
  onRemove: (threadId: string) => void;
}

export function MeHistorySection({
  historyItems,
  onClear,
  onOpenThread,
  onRefresh,
  onRemove,
}: MeHistorySectionProps) {
  return (
    <section id="history-section" className="px-1">
      <FluidDivider label="History" className="mb-8" />
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <div className="flex items-center justify-center gap-2">
          <Eye className="h-4 w-4 text-[var(--od-accent)]" />
          <h2 className="od-text-title">我的足迹</h2>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            onClick={onRefresh}
            className="od-inline-action od-inline-action-ghost"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            刷新
          </button>
          {historyItems.length > 0 && (
            <button
              type="button"
              onClick={onClear}
              className="od-inline-action od-inline-action-soft"
            >
              清空足迹
            </button>
          )}
        </div>
      </div>

      {historyItems.length === 0 ? (
        <div className="mx-auto max-w-3xl text-center">
          <p className="od-text-body">这里还空着呢。你点开帖子预览后，我会帮你把最近看过的内容记在这里。</p>
        </div>
      ) : (
        <div className="mx-auto flex max-w-4xl flex-col divide-y divide-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)] border-y border-[color-mix(in_srgb,var(--od-text-secondary)_14%,transparent)]">
          {historyItems.map((item) => (
            <div key={item.threadId} className="flex items-center gap-4 py-4">
              {item.thumbnailUrl ? (
                <button
                  type="button"
                  onClick={() => onOpenThread(item.threadId)}
                  className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-[var(--od-surface-soft)]"
                  title={`打开 ${item.title}`}
                >
                  <img src={item.thumbnailUrl} alt={item.title} className="h-full w-full object-cover" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => onOpenThread(item.threadId)}
                  className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-[color-mix(in_srgb,var(--od-surface-input)_68%,transparent)] text-[var(--od-text-tertiary)]"
                  title={`打开 ${item.title}`}
                >
                  <Eye className="h-5 w-5" />
                </button>
              )}

              <div className="min-w-0 flex-1">
                <button
                  type="button"
                  onClick={() => onOpenThread(item.threadId)}
                  className="block max-w-full truncate text-left text-base font-semibold text-[var(--od-text-primary)] transition-colors hover:text-[var(--od-accent)]"
                >
                  {item.title}
                </button>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-[var(--od-text-secondary)]">
                  {item.authorName && <span>@{item.authorName}</span>}
                  {item.channelId && <span>频道 {item.channelId}</span>}
                  <span>{new Date(item.visitedAt).toLocaleString('zh-CN', { hour12: false })}</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => onRemove(item.threadId)}
                className="shrink-0 p-2 text-[var(--od-text-tertiary)] transition-colors hover:text-[var(--od-text-primary)]"
                title="删除这条足迹"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
