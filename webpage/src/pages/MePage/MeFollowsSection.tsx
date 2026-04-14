import { Bookmark, RefreshCw } from 'lucide-react';

import { ThreadResultsCollection } from '@/entities/thread/ThreadResultsCollection';
import type { Thread } from '@/entities/thread/types';
import { FluidDivider } from '@/shared/ui/FluidDivider';

interface MeFollowsSectionProps {
  hasAnyResults: boolean;
  isError: boolean;
  isLoading: boolean;
  selectedChannel?: string | null;
  threads: Thread[];
  onClearChannel: () => void;
  onPreview: (thread: Thread) => void;
  onRefresh: () => void;
}

export function MeFollowsSection({
  hasAnyResults,
  isError,
  isLoading,
  selectedChannel,
  threads,
  onClearChannel,
  onPreview,
  onRefresh,
}: MeFollowsSectionProps) {
  return (
    <section className="px-1">
      <FluidDivider label="Follows" className="mb-8" />
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <div className="flex items-center justify-center gap-2">
          <Bookmark className="h-4 w-4 text-[var(--od-accent)]" />
          <h2 className="od-text-title">我的关注</h2>
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
          {selectedChannel && (
            <button
              type="button"
              onClick={onClearChannel}
              className="od-inline-action od-inline-action-soft"
            >
              清除频道筛选
            </button>
          )}
        </div>
      </div>

      {selectedChannel && (
        <p className="mb-5 text-center text-sm leading-6 text-[var(--od-text-secondary)]">
          现在只在当前频道里看关注内容，侧栏切频道会直接刷新这里的范围。
        </p>
      )}

      {isLoading ? (
        <p className="od-text-body">正在加载关注列表...</p>
      ) : isError ? (
        <p className="od-text-body text-[var(--od-text-emphasis)]">关注列表加载失败了，稍后试试看。</p>
      ) : !hasAnyResults ? (
        <p className="od-text-body">还没有关注任何内容，去广场看看有没有感兴趣的吧。</p>
      ) : threads.length === 0 ? (
        <p className="od-text-body">这个频道里暂时没有你关注的内容，换个频道看看会更快一点。</p>
      ) : (
        <ThreadResultsCollection threads={threads} onPreview={onPreview} />
      )}
    </section>
  );
}
