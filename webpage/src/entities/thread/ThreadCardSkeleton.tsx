export function ThreadCardSkeleton() {
  return (
    <article className="overflow-hidden rounded-xl bg-[var(--od-card)] shadow-md">
      {/* 图片骨架 - 使用渐变闪烁效果 */}
      <div className="aspect-[4/3] bg-gradient-to-r from-[var(--od-bg-tertiary)] via-[var(--od-bg-secondary)] to-[var(--od-bg-tertiary)] bg-[length:200%_100%] animate-shimmer" />

      {/* 内容骨架 */}
      <div className="p-3">
        {/* 标题骨架 */}
        <div className="mb-2 space-y-2">
          <div className="h-5 w-3/4 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer" />
          <div
            className="h-5 w-1/2 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
            style={{ animationDelay: '0.1s' }}
          />
        </div>

        {/* 作者信息骨架 */}
        <div className="mb-2 flex items-center gap-2">
          <div
            className="h-3 w-20 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
            style={{ animationDelay: '0.2s' }}
          />
          <div className="h-3 w-1 rounded bg-[var(--od-bg-secondary)]" />
          <div
            className="h-3 w-16 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
            style={{ animationDelay: '0.3s' }}
          />
        </div>

        {/* 摘要骨架 */}
        <div className="mb-3 h-20 space-y-2">
          <div
            className="h-3 w-full rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
            style={{ animationDelay: '0.4s' }}
          />
          <div
            className="h-3 w-full rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
            style={{ animationDelay: '0.5s' }}
          />
          <div
            className="h-3 w-4/5 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
            style={{ animationDelay: '0.6s' }}
          />
        </div>

        {/* 底部统计骨架 */}
        <div className="flex items-center justify-between border-t border-[var(--od-border)] pt-2">
          <div className="flex items-center gap-3">
            <div
              className="h-3 w-8 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
              style={{ animationDelay: '0.7s' }}
            />
            <div
              className="h-3 w-8 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
              style={{ animationDelay: '0.8s' }}
            />
          </div>
          <div
            className="h-4 w-4 rounded bg-gradient-to-r from-[var(--od-bg-secondary)] via-[var(--od-bg-tertiary)] to-[var(--od-bg-secondary)] bg-[length:200%_100%] animate-shimmer"
            style={{ animationDelay: '0.9s' }}
          />
        </div>
      </div>
    </article>
  );
}
