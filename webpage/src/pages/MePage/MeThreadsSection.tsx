import { FileText, RefreshCw } from 'lucide-react';

import { ThreadResultsCollection } from '@/entities/thread/ThreadResultsCollection';
import type { Thread } from '@/entities/thread/types';
import { FluidDivider } from '@/shared/ui/FluidDivider';

interface MeThreadsSectionProps {
  isLoading: boolean;
  threads: Thread[];
  totalReplies: number;
  totalReactions: number;
  totalThreads: number;
  onPreview: (thread: Thread) => void;
  onRefresh: () => void;
}

export function MeThreadsSection({
  isLoading,
  threads,
  totalReplies,
  totalReactions,
  totalThreads,
  onPreview,
  onRefresh,
}: MeThreadsSectionProps) {
  return (
    <section className="px-1">
      <FluidDivider label="Threads" className="mb-8" />
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <div className="flex items-center justify-center gap-2">
          <FileText className="h-4 w-4 text-[var(--od-accent)]" />
          <h2 className="od-text-title">我的创建</h2>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="od-inline-action od-inline-action-ghost"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </button>
      </div>

      <div className="mb-8 mx-auto grid max-w-4xl grid-cols-2 gap-x-6 gap-y-5 text-center sm:grid-cols-4">
        <div>
          <p className="text-sm font-medium text-[var(--od-text-secondary)]">帖子数</p>
          <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
            {totalThreads}
          </p>
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--od-text-secondary)]">累计点赞</p>
          <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
            {totalReactions}
          </p>
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--od-text-secondary)]">累计回复</p>
          <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
            {totalReplies}
          </p>
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--od-text-secondary)]">当前加载</p>
          <p className="mt-2 text-[1.5rem] font-semibold tracking-tight text-[var(--od-text-value)] tabular-nums">
            {threads.length}
          </p>
        </div>
      </div>

      {isLoading ? (
        <p className="od-text-body">正在加载你创建的内容...</p>
      ) : threads.length === 0 ? (
        <p className="od-text-body">还没有找到你创建的内容，可能还没被索引到。</p>
      ) : (
        <ThreadResultsCollection threads={threads} onPreview={onPreview} />
      )}
    </section>
  );
}
