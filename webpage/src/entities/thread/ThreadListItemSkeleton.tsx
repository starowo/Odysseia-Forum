import { MessageCircle, ThumbsUp } from 'lucide-react';

export function ThreadListItemSkeleton() {
  return (
    <article
      className="group relative flex min-h-[8rem] w-full max-w-full gap-0 overflow-hidden rounded-xl bg-[var(--od-card)] shadow-md md:h-48"
    >
      {/* 左侧内容区骨架 */}
      <div className="flex flex-1 flex-col justify-between p-3 min-w-0 md:p-5">
        <div className="space-y-3">
          {/* 标题骨架 */}
          <div className="h-6 w-3/4 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          
          {/* 作者和时间骨架 */}
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 animate-pulse rounded-full bg-[var(--od-bg-tertiary)] md:h-8 md:w-8" />
            <div className="h-4 w-24 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          </div>
        </div>

        {/* 摘要骨架 */}
        <div className="hidden space-y-2 md:block">
          <div className="h-3 w-full animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
          <div className="h-3 w-4/5 animate-shimmer rounded bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
        </div>

        {/* 底部统计骨架 */}
        <div className="flex items-center justify-between">
          <div className="flex gap-4">
            <div className="flex items-center gap-1">
              <MessageCircle className="h-3.5 w-3.5 text-[var(--od-text-tertiary)] opacity-30" />
              <div className="h-3 w-6 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
            </div>
            <div className="flex items-center gap-1">
              <ThumbsUp className="h-3.5 w-3.5 text-[var(--od-text-tertiary)] opacity-30" />
              <div className="h-3 w-6 animate-pulse rounded bg-[var(--od-bg-tertiary)]" />
            </div>
          </div>
          <div className="h-8 w-24 animate-pulse rounded-lg bg-[var(--od-bg-tertiary)]" />
        </div>
      </div>

      {/* 右侧图片占位骨架 (可选) */}
      <div className="hidden h-full w-48 animate-shimmer md:block bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-border-strong)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%]" />
    </article>
  );
}
